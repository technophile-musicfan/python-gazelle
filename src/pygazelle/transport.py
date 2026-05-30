from __future__ import annotations

import asyncio
import time

import httpx

from .errors import GazelleAPIError, GazelleAuthError, GazelleNotFoundError, GazelleRateLimitError


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
        _http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._ajax_url = f"{base_url}/ajax.php"
        self._login_url = f"{base_url}/login.php"
        self._username = username
        self._password = password
        self._api_key = api_key
        self._max_retries = max_retries
        self._auth_mode = "api_key" if api_key else "cookie" if username else None
        if self._auth_mode is None:
            raise ValueError("Either api_key or username+password must be provided")
        self._logged_in = False
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

    async def request(self, action: str, **params: str | int) -> dict:
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

    def _parse(self, response: httpx.Response) -> dict:
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
