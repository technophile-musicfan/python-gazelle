from __future__ import annotations

import httpx

from .errors import GazelleAPIError, GazelleAuthError, GazelleNotFoundError, GazelleRateLimitError


class GazelleTransport:
    def __init__(
        self,
        base_url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
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
        self._logged_in = False
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"token {api_key}"
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
        response = await self._client.get(
            self._ajax_url,
            params={"action": action, **params},
        )
        if (response.status_code in (401, 403)) and self._auth_mode == "cookie":
            await self._login()
            response = await self._client.get(
                self._ajax_url,
                params={"action": action, **params},
            )
        return self._parse(response)

    async def download(self, torrent_id: int) -> bytes:
        response = await self._client.get(
            self._ajax_url,
            params={"action": "download", "id": torrent_id},
        )
        if response.status_code == 404:
            raise GazelleNotFoundError(f"Torrent {torrent_id} not found")
        if not response.is_success:
            raise GazelleAPIError(status_code=response.status_code)
        return response.content

    def _parse(self, response: httpx.Response) -> dict:
        if response.status_code == 401 or response.status_code == 403:
            raise GazelleAuthError(f"HTTP {response.status_code}")
        if response.status_code == 404:
            raise GazelleNotFoundError("Resource not found")
        if response.status_code == 429:
            raise GazelleRateLimitError("Rate limit exceeded")
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
