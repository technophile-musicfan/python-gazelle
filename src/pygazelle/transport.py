from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol, TypedDict, final

import httpx

from .errors import GazelleAPIError, GazelleAuthError, GazelleNotFoundError, GazelleRateLimitError


class SupportsTransport(Protocol):
    """Structural interface the resources depend on.

    Both :class:`GazelleTransport` and the test stubs satisfy this, so resources
    are decoupled from the concrete transport implementation.
    """

    announce_host: str | None

    async def request(self, action: str, **params: str | int) -> dict[str, Any]: ...

    async def request_write(
        self,
        action: str,
        *,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, str | int] | None = None,
        include_auth_key: bool = True,
    ) -> dict[str, Any]: ...

    async def download(self, torrent_id: int) -> bytes: ...


class TransportOptions(TypedDict, total=False):
    """Optional :class:`GazelleTransport` settings the client subclasses forward."""

    api_key_prefix: str
    user_agent: str
    rate: float
    max_retries: int
    announce_host: str | None


@final
class TokenBucket:
    def __init__(self, rate: float = 3.0) -> None:
        self._rate = rate
        self._tokens = rate
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait)


@final
class GazelleTransport:
    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        api_key_prefix: str = "token ",
        user_agent: str = "python-gazelle",
        rate: float = 3.0,
        max_retries: int = 3,
        announce_host: str | None = None,
        _http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._ajax_url = f"{base_url}/ajax.php"
        self._login_url = f"{base_url}/login.php"
        self._username = username
        self._password = password
        self._api_key = api_key
        self._max_retries = max_retries
        self.announce_host = announce_host
        self._auth_mode = "api_key" if api_key else "cookie" if username else None
        if self._auth_mode is None:
            raise ValueError("Either api_key or username+password must be provided")
        self._logged_in = False
        self._auth_key: str | None = None
        self._rate_limiter = TokenBucket(rate)
        # RED rejects requests without a custom User-Agent (the library default
        # gets a 401); a UA is harmless/expected on the other trackers too.
        headers: dict[str, str] = {"User-Agent": user_agent}
        if api_key:
            # Trackers diverge on the API-key header: Orpheus expects
            # "token <key>" (the recommended Gazelle form), while RED expects
            # the bare key with no prefix. Each client supplies the right one.
            headers["Authorization"] = f"{api_key_prefix}{api_key}"
        if _http_client is not None:
            if headers:
                _http_client.headers.update(headers)
            self._client = _http_client
        else:
            self._client = httpx.AsyncClient(headers=headers)

    async def _login(self) -> None:
        response = await self._client.post(
            self._login_url,
            data={"username": self._username, "password": self._password, "keeplogged": "1"},
        )
        if not response.is_success:
            raise GazelleAuthError("Login failed")
        self._logged_in = True

    async def request(self, action: str, **params: str | int) -> dict[str, Any]:
        if self._auth_mode == "cookie" and not self._logged_in:
            await self._login()
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._rate_limiter.acquire()
            response = await self._client.get(
                self._ajax_url,
                params={"action": action, **params},
            )
            if response.status_code in (429, 500, 502, 503, 504):
                last_exc = (
                    GazelleRateLimitError("Rate limit exceeded")
                    if response.status_code == 429
                    else GazelleAPIError(status_code=response.status_code)
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt * 0.1)
                continue
            if response.status_code in (401, 403) and self._auth_mode == "cookie":
                last_exc = GazelleAuthError(f"HTTP {response.status_code}")
                await self._login()
                continue
            return self._parse(response)
        assert last_exc is not None
        raise last_exc

    async def _ensure_auth_key(self) -> str | None:
        """Fetch and cache the ``authkey`` Gazelle write actions require.

        It is returned in the ``index`` response; cached so repeated writes do
        not re-fetch it.
        """
        if self._auth_key is None:
            data = await self.request("index")
            self._auth_key = data.get("authkey")
        return self._auth_key

    async def request_write(
        self,
        action: str,
        *,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, str | int] | None = None,
        include_auth_key: bool = True,
    ) -> dict[str, Any]:
        """POST a mutating ``action`` to ``ajax.php``.

        ``data`` is the form/multipart body, ``files`` the multipart file parts
        (e.g. an uploaded log), and ``params`` any extra query-string params some
        actions read from the query (e.g. add_log's ``id``).

        Unlike :meth:`request` (GET), this performs **no retry on 429/5xx**:
        a write that already took effect server-side but returned a transient
        error must not be re-sent (it would double-apply). The only retry is a
        single re-auth on a cookie-mode 401, which means the request was
        rejected before processing (provably never landed).
        """
        if self._auth_mode == "cookie" and not self._logged_in:
            await self._login()
        body: dict[str, Any] = dict(data or {})
        if include_auth_key and "auth" not in body:
            auth_key = await self._ensure_auth_key()
            if auth_key is not None:
                body["auth"] = auth_key
        response = await self._post_write(action, body, files, params)
        if response.status_code == 401 and self._auth_mode == "cookie":
            # Session expired; the write was rejected (not processed). Safe to
            # re-auth and resend exactly once. Only 401 (not 403) — a 403 is
            # "forbidden", not an expired session, so re-sending a write on it
            # is pointless churn and against the no-retry-on-writes intent.
            await self._login()
            response = await self._post_write(action, body, files, params)
        if response.status_code == 429:
            raise GazelleRateLimitError("Rate limit exceeded")
        return self._parse(response)

    async def _post_write(
        self,
        action: str,
        body: dict[str, Any],
        files: Any | None,
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response:
        await self._rate_limiter.acquire()
        return await self._client.post(
            self._ajax_url,
            params={"action": action, **(params or {})},
            data=body,
            files=files,
        )

    async def download(self, torrent_id: int) -> bytes:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._rate_limiter.acquire()
            response = await self._client.get(
                self._ajax_url,
                params={"action": "download", "id": torrent_id},
            )
            if response.status_code in (500, 502, 503, 504):
                last_exc = GazelleAPIError(status_code=response.status_code)
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt * 0.1)
                continue
            if response.status_code == 404:
                raise GazelleNotFoundError(f"Torrent {torrent_id} not found")
            if not response.is_success:
                raise GazelleAPIError(status_code=response.status_code)
            return response.content
        assert last_exc is not None
        raise last_exc

    def _parse(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 401 or response.status_code == 403:
            raise GazelleAuthError(f"HTTP {response.status_code}")
        if response.status_code == 404:
            raise GazelleNotFoundError("Resource not found")
        if not response.is_success:
            raise GazelleAPIError(status_code=response.status_code)
        data = response.json()
        if data.get("status") != "success":
            raise GazelleAPIError(status_code=200, message=data.get("error", "unknown error"))
        return data["response"]

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GazelleTransport:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
