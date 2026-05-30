# Core API Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational Gazelle API client library — async-native transport, resource-based API surface, Pydantic v2 response models, Orpheus/Redacted tracker subclasses, and a sync wrapper backed by a persistent background event loop.

**Architecture:** Three layers: `GazelleTransport` (httpx, auth, token-bucket rate limiting, exponential backoff retry) → `GazelleClient` with resource namespaces (`OrpheusClient`/`RedactedClient` subclasses) → `GazelleSyncClient` using `_SyncProxy` over a daemon-thread event loop. All responses are Pydantic v2 models with camelCase↔snake_case alias generation.

**Tech Stack:** Python 3.11+, httpx (async HTTP), pydantic v2, asyncio, python-dotenv, pytest, pytest-asyncio

---

## File Map

```
src/pygazelle/
  __init__.py               # public exports
  errors.py                 # GazelleError hierarchy
  transport.py              # GazelleTransport, TokenBucket
  client.py                 # GazelleClient, OrpheusClient, RedactedClient
  sync.py                   # _BackgroundLoop, _SyncProxy, GazelleSyncClient, tracker sync classes
  resources/
    __init__.py
    base.py                 # BaseResource
    torrents.py             # TorrentResource
    artists.py              # ArtistResource
    requests.py             # RequestResource
    collages.py             # CollageResource
    user.py                 # UserResource
    inbox.py                # InboxResource
    notifications.py        # NotificationResource
  models/
    __init__.py
    base.py                 # GazelleModel (Pydantic base with camelCase alias)
    torrents.py             # Torrent, TorrentGroup, TorrentResult
    artists.py              # Artist, ArtistResult
    requests.py             # Request, RequestResult
    collages.py             # Collage
    user.py                 # User, UserStats
    inbox.py                # Message
    notifications.py        # Notification

tests/
  conftest.py               # load_dotenv, shared fixtures
  test_errors.py
  test_transport.py         # unit tests with mock httpx transport
  test_client.py            # resource + client unit tests
  test_sync.py              # sync wrapper tests
  models/
    conftest.py             # fixture loading helper
    test_torrents.py
    test_artists.py
    test_user.py
    test_notifications.py
  integration/
    conftest.py             # skip markers, credential fixtures
    test_orpheus.py
    test_redacted.py
  fixtures/
    orpheus/
      torrent.json
      artist.json
      index.json
      notifications.json
    redacted/
      torrent.json
      artist.json
      index.json
      notifications.json
```

---

## Task 1: Project Setup

**Files:**
- Modify: `pyproject.toml`
- Create: all skeleton files listed in File Map

- [ ] **Step 1.1: Add runtime dependencies**

In `pyproject.toml`, update the `dependencies` list:

```toml
dependencies = [
    "httpx>=0.28",
    "pydantic>=2.0",
]
```

- [ ] **Step 1.2: Add dev dependencies**

In `pyproject.toml`, update `[dependency-groups] dev`:

```toml
dev = [
    "pytest>=9.0.3",
    "pytest-sugar>=1.1.1",
    "pytest-asyncio>=0.24",
    "ruff>=0.15.12",
    "codespell>=2.4.2",
    "rich>=15.0.0",
    "basedpyright>=1.39.3",
    "funlog>=0.2.1",
    "python-dotenv>=1.0",
]
```

- [ ] **Step 1.3: Configure pytest-asyncio**

In `pyproject.toml`, add to `[tool.pytest.ini_options]`:

```toml
asyncio_mode = "auto"
```

- [ ] **Step 1.4: Sync dependencies**

```bash
uv sync
```

Expected: all packages installed without errors.

- [ ] **Step 1.5: Create module skeleton**

```bash
# resources package
mkdir -p src/pygazelle/resources src/pygazelle/models
touch src/pygazelle/errors.py src/pygazelle/transport.py src/pygazelle/client.py src/pygazelle/sync.py
touch src/pygazelle/resources/__init__.py src/pygazelle/resources/base.py
touch src/pygazelle/resources/torrents.py src/pygazelle/resources/artists.py
touch src/pygazelle/resources/requests.py src/pygazelle/resources/collages.py
touch src/pygazelle/resources/user.py src/pygazelle/resources/inbox.py
touch src/pygazelle/resources/notifications.py
touch src/pygazelle/models/__init__.py src/pygazelle/models/base.py
touch src/pygazelle/models/torrents.py src/pygazelle/models/artists.py
touch src/pygazelle/models/requests.py src/pygazelle/models/collages.py
touch src/pygazelle/models/user.py src/pygazelle/models/inbox.py
touch src/pygazelle/models/notifications.py

# test structure
mkdir -p tests/models tests/integration tests/fixtures/orpheus tests/fixtures/redacted
touch tests/conftest.py tests/test_errors.py tests/test_transport.py
touch tests/test_client.py tests/test_sync.py
touch tests/models/conftest.py
touch tests/models/test_torrents.py tests/models/test_artists.py
touch tests/models/test_user.py tests/models/test_notifications.py
touch tests/integration/conftest.py
touch tests/integration/test_orpheus.py tests/integration/test_redacted.py
```

- [ ] **Step 1.6: Commit**

```bash
git add pyproject.toml src/pygazelle/ tests/
git commit -m "chore: project setup — deps and module skeleton"
```

---

## Task 2: Error Hierarchy

**Files:**
- Create: `src/pygazelle/errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 2.1: Write the failing tests**

`tests/test_errors.py`:

```python
import pytest
from pygazelle.errors import (
    GazelleError,
    GazelleAuthError,
    GazelleRateLimitError,
    GazelleNotFoundError,
    GazelleAPIError,
)


def test_all_errors_are_gazelle_errors():
    assert issubclass(GazelleAuthError, GazelleError)
    assert issubclass(GazelleRateLimitError, GazelleError)
    assert issubclass(GazelleNotFoundError, GazelleError)
    assert issubclass(GazelleAPIError, GazelleError)


def test_api_error_stores_status_code():
    err = GazelleAPIError(status_code=500, message="server error")
    assert err.status_code == 500


def test_api_error_message_includes_status_code():
    err = GazelleAPIError(status_code=500, message="server error")
    assert "500" in str(err)


def test_gazelle_error_is_exception():
    assert issubclass(GazelleError, Exception)
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_errors.py -v
```

Expected: `ImportError` — `errors.py` is empty.

- [ ] **Step 2.3: Implement errors.py**

`src/pygazelle/errors.py`:

```python
class GazelleError(Exception):
    pass


class GazelleAuthError(GazelleError):
    pass


class GazelleRateLimitError(GazelleError):
    pass


class GazelleNotFoundError(GazelleError):
    pass


class GazelleAPIError(GazelleError):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_errors.py -v
```

Expected: 4 passed.

- [ ] **Step 2.5: Commit**

```bash
git add src/pygazelle/errors.py tests/test_errors.py
git commit -m "feat: add GazelleError hierarchy"
```

---

## Task 3: Transport — Core Request & JSON Parsing

**Files:**
- Create: `src/pygazelle/transport.py`
- Create: `tests/test_transport.py`

The Gazelle API uses: `GET /ajax.php?action=<action>&<params>` and returns `{"status": "success", "response": {...}}` or `{"status": "failure", "error": "..."}`.

- [ ] **Step 3.1: Write the mock transport helper and core request tests**

`tests/test_transport.py`:

```python
import pytest
import httpx
from pygazelle.transport import GazelleTransport
from pygazelle.errors import GazelleAPIError, GazelleNotFoundError


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[tuple[int, dict | bytes]]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._responses[self._index % len(self._responses)]
        self._index += 1
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)


def make_transport(responses: list[tuple[int, dict | bytes]], **kwargs) -> tuple[GazelleTransport, MockTransport]:
    mock = MockTransport(responses)
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport("https://example.com", api_key="test", _http_client=client, **kwargs)
    return transport, mock


async def test_request_returns_response_dict():
    transport, _ = make_transport([
        (200, {"status": "success", "response": {"id": 1, "name": "Album"}}),
    ])
    async with transport:
        result = await transport.request("torrent", id=1)
    assert result == {"id": 1, "name": "Album"}


async def test_request_raises_on_failure_status():
    transport, _ = make_transport([
        (200, {"status": "failure", "error": "bad id parameter"}),
    ])
    async with transport:
        with pytest.raises(GazelleAPIError):
            await transport.request("torrent", id=999)


async def test_request_raises_not_found_on_404():
    transport, _ = make_transport([(404, b"")])
    async with transport:
        with pytest.raises(GazelleNotFoundError):
            await transport.request("torrent", id=999)


async def test_request_sends_action_as_query_param():
    transport, mock = make_transport([
        (200, {"status": "success", "response": {}}),
    ])
    async with transport:
        await transport.request("index")
    assert b"action=index" in mock.requests[0].url.query


async def test_download_returns_bytes():
    transport, _ = make_transport([(200, b"torrent-data")])
    async with transport:
        result = await transport.download(42)
    assert result == b"torrent-data"
```

- [ ] **Step 3.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_transport.py -v
```

Expected: `ImportError` — `transport.py` is empty.

- [ ] **Step 3.3: Implement transport foundation**

`src/pygazelle/transport.py`:

```python
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
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"token {api_key}"
        self._client = _http_client or httpx.AsyncClient(headers=headers)

    async def request(self, action: str, **params: str | int) -> dict:
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
```

- [ ] **Step 3.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_transport.py -v
```

Expected: 5 passed.

- [ ] **Step 3.5: Commit**

```bash
git add src/pygazelle/transport.py tests/test_transport.py
git commit -m "feat: add GazelleTransport with core request and JSON parsing"
```

---

## Task 4: Transport — Authentication

**Files:**
- Modify: `src/pygazelle/transport.py`
- Modify: `tests/test_transport.py`

- [ ] **Step 4.1: Write auth tests**

Append to `tests/test_transport.py`:

```python
async def test_api_key_sent_as_authorization_header():
    transport, mock = make_transport([
        (200, {"status": "success", "response": {}}),
    ])
    async with transport:
        await transport.request("index")
    assert mock.requests[0].headers.get("authorization") == "token test"


async def test_cookie_auth_calls_login_on_first_request():
    mock = MockTransport([
        (200, b""),                                          # login POST
        (200, {"status": "success", "response": {"id": 1}}),  # API call
    ])
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com",
        username="user",
        password="pass",
        _http_client=client,
    )
    async with transport:
        result = await transport.request("index")
    assert len(mock.requests) == 2
    assert mock.requests[0].method == "POST"
    assert result == {"id": 1}


async def test_cookie_auth_reauths_on_401():
    mock = MockTransport([
        (200, b""),    # initial login
        (401, b""),    # 401 on first API call → triggers re-auth
        (200, b""),    # re-login
        (200, {"status": "success", "response": {"id": 99}}),  # retry succeeds
    ])
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com",
        username="user",
        password="pass",
        _http_client=client,
    )
    async with transport:
        result = await transport.request("index")
    assert result == {"id": 99}
```

- [ ] **Step 4.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_transport.py::test_api_key_sent_as_authorization_header tests/test_transport.py::test_cookie_auth_calls_login_on_first_request tests/test_transport.py::test_cookie_auth_reauths_on_401 -v
```

Expected: first test passes (header already set), remaining two fail.

- [ ] **Step 4.3: Implement cookie auth and re-auth**

Replace `GazelleTransport.request` and add `_login` in `src/pygazelle/transport.py`:

```python
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
```

Also add `self._logged_in = False` in `__init__` after the `_auth_mode` assignment.

- [ ] **Step 4.4: Run all transport tests**

```bash
uv run pytest tests/test_transport.py -v
```

Expected: all pass.

- [ ] **Step 4.5: Commit**

```bash
git add src/pygazelle/transport.py tests/test_transport.py
git commit -m "feat: add cookie and API key auth to GazelleTransport"
```

---

## Task 5: Token-Bucket Rate Limiter

**Files:**
- Modify: `src/pygazelle/transport.py`
- Modify: `tests/test_transport.py`

- [ ] **Step 5.1: Write rate limiter tests**

Append to `tests/test_transport.py`:

```python
import time
from pygazelle.transport import TokenBucket


async def test_token_bucket_allows_first_request_immediately():
    bucket = TokenBucket(rate=3.0)
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1  # no wait for first token


async def test_token_bucket_with_high_rate_does_not_wait():
    bucket = TokenBucket(rate=1000.0)
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1


async def test_transport_respects_custom_rate():
    # With rate=1000, 5 requests should complete nearly instantly
    transport, mock = make_transport(
        [(200, {"status": "success", "response": {}}) for _ in range(5)],
        rate=1000.0,
    )
    start = time.monotonic()
    async with transport:
        for _ in range(5):
            await transport.request("index")
    elapsed = time.monotonic() - start
    assert elapsed < 1.0
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_transport.py::test_token_bucket_allows_first_request_immediately tests/test_transport.py::test_token_bucket_with_high_rate_does_not_wait tests/test_transport.py::test_transport_respects_custom_rate -v
```

Expected: `ImportError` — `TokenBucket` not defined yet.

- [ ] **Step 5.3: Implement TokenBucket**

Add to `src/pygazelle/transport.py` (before `GazelleTransport`):

```python
import asyncio
import time


class TokenBucket:
    def __init__(self, rate: float = 3.0) -> None:
        self._rate = rate
        self._tokens = rate
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last_refill = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0
```

Wire it into `GazelleTransport.__init__` (add `self._rate_limiter = TokenBucket(rate)`) and call `await self._rate_limiter.acquire()` at the start of `request()` (after the cookie login check, before the GET call).

- [ ] **Step 5.4: Run all transport tests**

```bash
uv run pytest tests/test_transport.py -v
```

Expected: all pass.

- [ ] **Step 5.5: Commit**

```bash
git add src/pygazelle/transport.py tests/test_transport.py
git commit -m "feat: add token-bucket rate limiter to GazelleTransport"
```

---

## Task 6: Transport — Retry & Complete Error Mapping

**Files:**
- Modify: `src/pygazelle/transport.py`
- Modify: `tests/test_transport.py`

- [ ] **Step 6.1: Write retry tests**

Append to `tests/test_transport.py`:

```python
async def test_retries_on_429():
    transport, mock = make_transport([
        (429, b""),
        (429, b""),
        (200, {"status": "success", "response": {"ok": True}}),
    ], max_retries=3)
    async with transport:
        result = await transport.request("index")
    assert result == {"ok": True}
    assert mock._index == 3


async def test_retries_on_500():
    transport, mock = make_transport([
        (500, b""),
        (200, {"status": "success", "response": {"ok": True}}),
    ], max_retries=3)
    async with transport:
        result = await transport.request("index")
    assert result == {"ok": True}


async def test_raises_rate_limit_error_after_max_retries():
    transport, _ = make_transport(
        [(429, b"")] * 4,
        max_retries=3,
    )
    async with transport:
        with pytest.raises(GazelleRateLimitError):
            await transport.request("index")


async def test_does_not_retry_on_404():
    transport, mock = make_transport([(404, b""), (200, {"status": "success", "response": {}})])
    async with transport:
        with pytest.raises(GazelleNotFoundError):
            await transport.request("torrent", id=1)
    assert mock._index == 1  # only one request made
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_transport.py::test_retries_on_429 tests/test_transport.py::test_retries_on_500 tests/test_transport.py::test_raises_rate_limit_error_after_max_retries tests/test_transport.py::test_does_not_retry_on_404 -v
```

Expected: failures — no retry logic yet.

- [ ] **Step 6.3: Implement retry loop**

Replace `GazelleTransport.request` with a version that has retry logic. The rate limiter acquire and cookie-login logic remain. Add `import asyncio` at the top of the file if not already present.

```python
    async def request(self, action: str, **params: str | int) -> dict:
        if self._auth_mode == "cookie" and not self._logged_in:
            await self._login()
        await self._rate_limiter.acquire()
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
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
                await self._login()
                continue
            return self._parse(response)
        assert last_exc is not None
        raise last_exc
```

- [ ] **Step 6.4: Run all transport tests**

```bash
uv run pytest tests/test_transport.py -v
```

Expected: all pass.

- [ ] **Step 6.5: Commit**

```bash
git add src/pygazelle/transport.py tests/test_transport.py
git commit -m "feat: add exponential backoff retry to GazelleTransport"
```

---

## Task 7: Pydantic Response Models

**Files:**
- Create: `src/pygazelle/models/base.py`
- Create: `src/pygazelle/models/torrents.py`
- Create: `src/pygazelle/models/artists.py`
- Create: `src/pygazelle/models/requests.py`
- Create: `src/pygazelle/models/collages.py`
- Create: `src/pygazelle/models/user.py`
- Create: `src/pygazelle/models/inbox.py`
- Create: `src/pygazelle/models/notifications.py`
- Create: `src/pygazelle/models/__init__.py`

- [ ] **Step 7.1: Implement the shared base model**

`src/pygazelle/models/base.py`:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class GazelleModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",  # tolerate undocumented fields
    )
```

`extra="ignore"` is critical: the Gazelle API returns undocumented fields that would break strict models.

- [ ] **Step 7.2: Implement torrent models**

`src/pygazelle/models/torrents.py`:

```python
from .base import GazelleModel


class TorrentArtist(GazelleModel):
    id: int
    name: str


class TorrentGroup(GazelleModel):
    id: int
    name: str
    year: int
    tags: list[str] = []
    artists: list[TorrentArtist] = []


class Torrent(GazelleModel):
    id: int
    info_hash: str
    media: str
    format: str
    encoding: str
    remastered: bool
    scene: bool
    has_log: bool
    has_cue: bool
    log_score: int
    file_count: int
    size: int
    seeders: int
    leechers: int
    snatched: int
    free_torrent: bool
    time: str
    file_path: str
    user_id: int
    username: str
    group: TorrentGroup | None = None


class TorrentResult(GazelleModel):
    group_id: int
    group_name: str
    artist: str
    tags: list[str] = []
    group_year: int
    max_size: int
    total_seeders: int
    total_leechers: int
    total_snatched: int
```

- [ ] **Step 7.3: Implement artist models**

`src/pygazelle/models/artists.py`:

```python
from .base import GazelleModel


class Artist(GazelleModel):
    id: int
    name: str
    body: str = ""
    image: str = ""
    tags: list[str] = []


class ArtistResult(GazelleModel):
    id: int
    name: str
```

- [ ] **Step 7.4: Implement remaining models**

`src/pygazelle/models/requests.py`:

```python
from .base import GazelleModel


class Request(GazelleModel):
    id: int
    title: str
    year: int
    artists: list[str] = []
    tags: list[str] = []
    description: str = ""


class RequestResult(GazelleModel):
    request_id: int
    title: str
    year: int
    artists: list[str] = []
```

`src/pygazelle/models/collages.py`:

```python
from .base import GazelleModel


class Collage(GazelleModel):
    id: int
    name: str
    description: str = ""
    tags: list[str] = []
    num_torrents: int = 0
```

`src/pygazelle/models/user.py`:

```python
from .base import GazelleModel


class UserStats(GazelleModel):
    uploaded: int
    downloaded: int
    ratio: float
    required_ratio: float


class User(GazelleModel):
    id: int
    username: str
    userstats: UserStats | None = None
```

`src/pygazelle/models/inbox.py`:

```python
from .base import GazelleModel


class Message(GazelleModel):
    conversation_id: int
    subject: str
    sender_id: int
    sender_name: str
    sent_date: str
    sticky: bool = False
    unread: bool = False
```

`src/pygazelle/models/notifications.py`:

```python
from .base import GazelleModel


class Notification(GazelleModel):
    torrent_id: int
    torrent_group_id: int
    group_name: str
    format: str = ""
    notification_type: str = ""
```

- [ ] **Step 7.5: Populate models/__init__.py**

`src/pygazelle/models/__init__.py`:

```python
from .artists import Artist, ArtistResult
from .collages import Collage
from .inbox import Message
from .notifications import Notification
from .requests import Request, RequestResult
from .torrents import Torrent, TorrentGroup, TorrentResult
from .user import User, UserStats

__all__ = [
    "Artist", "ArtistResult",
    "Collage",
    "Message",
    "Notification",
    "Request", "RequestResult",
    "Torrent", "TorrentGroup", "TorrentResult",
    "User", "UserStats",
]
```

- [ ] **Step 7.6: Run existing tests to confirm nothing is broken**

```bash
uv run pytest tests/test_errors.py tests/test_transport.py -v
```

Expected: all pass.

- [ ] **Step 7.7: Commit**

```bash
git add src/pygazelle/models/
git commit -m "feat: add Pydantic v2 response models for all Gazelle resources"
```

---

## Task 8: Resource Layer

**Files:**
- Create: `src/pygazelle/resources/base.py`
- Create: `src/pygazelle/resources/torrents.py`
- Create: `src/pygazelle/resources/artists.py`
- Create: `src/pygazelle/resources/requests.py`
- Create: `src/pygazelle/resources/collages.py`
- Create: `src/pygazelle/resources/user.py`
- Create: `src/pygazelle/resources/inbox.py`
- Create: `src/pygazelle/resources/notifications.py`
- Create: `tests/test_client.py`

- [ ] **Step 8.1: Implement BaseResource**

`src/pygazelle/resources/base.py`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..transport import GazelleTransport


class BaseResource:
    def __init__(self, transport: GazelleTransport) -> None:
        self._transport = transport
```

- [ ] **Step 8.2: Write resource tests**

`tests/test_client.py`:

```python
import pytest
import httpx
from pygazelle.transport import GazelleTransport
from pygazelle.resources.torrents import TorrentResource
from pygazelle.resources.artists import ArtistResource
from pygazelle.resources.user import UserResource
from pygazelle.resources.notifications import NotificationResource
from pygazelle.models import Torrent, Artist, User, Notification


class StubTransport:
    def __init__(self, responses: dict[str, dict]) -> None:
        self._responses = responses

    async def request(self, action: str, **params) -> dict:
        return self._responses[action]

    async def download(self, torrent_id: int) -> bytes:
        return b"fake-torrent-data"


async def test_torrent_resource_get_returns_torrent_model():
    stub = StubTransport({
        "torrent": {
            "group": {"id": 1, "name": "Album", "year": 2020, "tags": [], "artists": []},
            "torrent": {
                "id": 100, "infoHash": "ABC", "media": "CD", "format": "FLAC",
                "encoding": "Lossless", "remastered": False, "scene": False,
                "hasLog": True, "hasCue": True, "logScore": 100, "fileCount": 12,
                "size": 500000000, "seeders": 10, "leechers": 1, "snatched": 50,
                "freeTorrent": False, "time": "2020-01-01 00:00:00",
                "filePath": "Artist - Album", "userId": 1, "username": "uploader",
            },
        }
    })
    resource = TorrentResource(stub)
    torrent = await resource.get(100)
    assert isinstance(torrent, Torrent)
    assert torrent.id == 100
    assert torrent.format == "FLAC"


async def test_torrent_resource_download_returns_bytes():
    stub = StubTransport({})
    resource = TorrentResource(stub)
    data = await resource.download(100)
    assert data == b"fake-torrent-data"


async def test_artist_resource_get_returns_artist_model():
    stub = StubTransport({
        "artist": {"id": 1, "name": "Radiohead", "body": "", "image": "", "tags": []}
    })
    resource = ArtistResource(stub)
    artist = await resource.get(1)
    assert isinstance(artist, Artist)
    assert artist.name == "Radiohead"


async def test_user_resource_me_returns_user_model():
    stub = StubTransport({
        "index": {
            "id": 42, "username": "myuser",
            "userstats": {"uploaded": 1000, "downloaded": 500, "ratio": 2.0, "requiredRatio": 0.6},
        }
    })
    resource = UserResource(stub)
    user = await resource.me()
    assert isinstance(user, User)
    assert user.username == "myuser"


async def test_notification_resource_list_returns_notifications():
    stub = StubTransport({
        "notifications": {
            "results": [
                {
                    "torrentId": 1, "torrentGroupId": 10, "groupName": "Album",
                    "format": "FLAC", "notificationType": "Upload Deleted",
                }
            ]
        }
    })
    resource = NotificationResource(stub)
    notifications = await resource.list()
    assert len(notifications) == 1
    assert isinstance(notifications[0], Notification)
    assert notifications[0].notification_type == "Upload Deleted"
```

- [ ] **Step 8.3: Run tests to verify they fail**

```bash
uv run pytest tests/test_client.py -v
```

Expected: `ImportError` — resource files are empty.

- [ ] **Step 8.4: Implement TorrentResource**

`src/pygazelle/resources/torrents.py`:

```python
from .base import BaseResource
from ..models.torrents import Torrent, TorrentResult


class TorrentResource(BaseResource):
    async def get(self, torrent_id: int) -> Torrent:
        data = await self._transport.request("torrent", id=torrent_id)
        return Torrent.model_validate({**data["torrent"], "group": data.get("group")})

    async def search(self, query: str, **params: str | int) -> list[TorrentResult]:
        data = await self._transport.request("browse", searchstr=query, **params)
        return [TorrentResult.model_validate(r) for r in data.get("results", [])]

    async def download(self, torrent_id: int) -> bytes:
        return await self._transport.download(torrent_id)
```

- [ ] **Step 8.5: Implement ArtistResource**

`src/pygazelle/resources/artists.py`:

```python
from .base import BaseResource
from ..models.artists import Artist, ArtistResult


class ArtistResource(BaseResource):
    async def get(self, artist_id: int) -> Artist:
        data = await self._transport.request("artist", id=artist_id)
        return Artist.model_validate(data)

    async def search(self, name: str) -> list[ArtistResult]:
        data = await self._transport.request("browse", searchstr=name, artistname=name)
        seen: dict[int, ArtistResult] = {}
        for result in data.get("results", []):
            artist_id = result.get("artistId")
            if artist_id and artist_id not in seen:
                seen[artist_id] = ArtistResult(id=artist_id, name=result.get("artist", ""))
        return list(seen.values())
```

- [ ] **Step 8.6: Implement remaining resources**

`src/pygazelle/resources/requests.py`:

```python
from .base import BaseResource
from ..models.requests import Request, RequestResult


class RequestResource(BaseResource):
    async def get(self, request_id: int) -> Request:
        data = await self._transport.request("request", id=request_id)
        return Request.model_validate(data)

    async def search(self, query: str, **params: str | int) -> list[RequestResult]:
        data = await self._transport.request("requests", search=query, **params)
        return [RequestResult.model_validate(r) for r in data.get("results", [])]
```

`src/pygazelle/resources/collages.py`:

```python
from .base import BaseResource
from ..models.collages import Collage


class CollageResource(BaseResource):
    async def get(self, collage_id: int) -> Collage:
        data = await self._transport.request("collage", id=collage_id)
        return Collage.model_validate(data)
```

`src/pygazelle/resources/user.py`:

```python
from .base import BaseResource
from ..models.user import User


class UserResource(BaseResource):
    async def me(self) -> User:
        data = await self._transport.request("index")
        return User.model_validate(data)
```

`src/pygazelle/resources/inbox.py`:

```python
from .base import BaseResource
from ..models.inbox import Message


class InboxResource(BaseResource):
    async def list(self, **params: str | int) -> list[Message]:
        data = await self._transport.request("inbox", type="inbox", **params)
        return [Message.model_validate(m) for m in data.get("messages", [])]

    async def get(self, conversation_id: int) -> list[Message]:
        data = await self._transport.request("inbox", type="viewconv", id=conversation_id)
        return [Message.model_validate(m) for m in data.get("messages", [])]
```

`src/pygazelle/resources/notifications.py`:

```python
from .base import BaseResource
from ..models.notifications import Notification


class NotificationResource(BaseResource):
    async def list(self, **params: str | int) -> list[Notification]:
        data = await self._transport.request("notifications", **params)
        return [Notification.model_validate(n) for n in data.get("results", [])]
```

- [ ] **Step 8.7: Populate resources/__init__.py**

`src/pygazelle/resources/__init__.py`:

```python
from .artists import ArtistResource
from .collages import CollageResource
from .inbox import InboxResource
from .notifications import NotificationResource
from .requests import RequestResource
from .torrents import TorrentResource
from .user import UserResource

__all__ = [
    "ArtistResource", "CollageResource", "InboxResource",
    "NotificationResource", "RequestResource", "TorrentResource", "UserResource",
]
```

- [ ] **Step 8.8: Run all tests**

```bash
uv run pytest tests/test_client.py -v
```

Expected: all pass.

- [ ] **Step 8.9: Commit**

```bash
git add src/pygazelle/resources/ tests/test_client.py
git commit -m "feat: add resource layer (TorrentResource and all other resources)"
```

---

## Task 9: GazelleClient + Tracker Subclasses

**Files:**
- Create: `src/pygazelle/client.py`
- Modify: `tests/test_client.py`

- [ ] **Step 9.1: Write client tests**

Append to `tests/test_client.py`:

```python
import httpx
from pygazelle.client import GazelleClient, OrpheusClient, RedactedClient
from pygazelle.transport import GazelleTransport
from pygazelle.resources.torrents import TorrentResource
from pygazelle.resources.artists import ArtistResource
from pygazelle.resources.notifications import NotificationResource


class MockTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "success", "response": {}})


def make_client() -> GazelleClient:
    http = httpx.AsyncClient(transport=MockTransport())
    transport = GazelleTransport("https://example.com", api_key="k", _http_client=http)
    return GazelleClient(transport)


def test_client_exposes_resource_namespaces():
    client = make_client()
    assert isinstance(client.torrents, TorrentResource)
    assert isinstance(client.artists, ArtistResource)
    assert isinstance(client.notifications, NotificationResource)
    assert hasattr(client, "requests")
    assert hasattr(client, "collages")
    assert hasattr(client, "user")
    assert hasattr(client, "inbox")


def test_orpheus_client_uses_orpheus_url():
    client = OrpheusClient(api_key="k")
    assert "orpheus.network" in client._transport._ajax_url


def test_redacted_client_uses_redacted_url():
    client = RedactedClient(api_key="k")
    assert "redacted.ch" in client._transport._ajax_url
```

- [ ] **Step 9.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_client.py::test_client_exposes_resource_namespaces tests/test_client.py::test_orpheus_client_uses_orpheus_url tests/test_client.py::test_redacted_client_uses_redacted_url -v
```

Expected: `ImportError` — `client.py` is empty.

- [ ] **Step 9.3: Implement client.py**

`src/pygazelle/client.py`:

```python
from __future__ import annotations

from .transport import GazelleTransport
from .resources.artists import ArtistResource
from .resources.collages import CollageResource
from .resources.inbox import InboxResource
from .resources.notifications import NotificationResource
from .resources.requests import RequestResource
from .resources.torrents import TorrentResource
from .resources.user import UserResource

ORPHEUS_BASE_URL = "https://orpheus.network"
REDACTED_BASE_URL = "https://redacted.ch"


class GazelleClient:
    def __init__(self, transport: GazelleTransport) -> None:
        self._transport = transport
        self._torrents: TorrentResource | None = None
        self._artists: ArtistResource | None = None
        self._requests: RequestResource | None = None
        self._collages: CollageResource | None = None
        self._user: UserResource | None = None
        self._inbox: InboxResource | None = None
        self._notifications: NotificationResource | None = None

    @property
    def torrents(self) -> TorrentResource:
        if self._torrents is None:
            self._torrents = TorrentResource(self._transport)
        return self._torrents

    @property
    def artists(self) -> ArtistResource:
        if self._artists is None:
            self._artists = ArtistResource(self._transport)
        return self._artists

    @property
    def requests(self) -> RequestResource:
        if self._requests is None:
            self._requests = RequestResource(self._transport)
        return self._requests

    @property
    def collages(self) -> CollageResource:
        if self._collages is None:
            self._collages = CollageResource(self._transport)
        return self._collages

    @property
    def user(self) -> UserResource:
        if self._user is None:
            self._user = UserResource(self._transport)
        return self._user

    @property
    def inbox(self) -> InboxResource:
        if self._inbox is None:
            self._inbox = InboxResource(self._transport)
        return self._inbox

    @property
    def notifications(self) -> NotificationResource:
        if self._notifications is None:
            self._notifications = NotificationResource(self._transport)
        return self._notifications

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> GazelleClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


class OrpheusClient(GazelleClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            GazelleTransport(ORPHEUS_BASE_URL, username=username, password=password, api_key=api_key, **kwargs)
        )


class RedactedClient(GazelleClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            GazelleTransport(REDACTED_BASE_URL, username=username, password=password, api_key=api_key, **kwargs)
        )
```

- [ ] **Step 9.4: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: all pass.

- [ ] **Step 9.5: Commit**

```bash
git add src/pygazelle/client.py tests/test_client.py
git commit -m "feat: add GazelleClient, OrpheusClient, RedactedClient"
```

---

## Task 10: Sync Wrapper

**Files:**
- Create: `src/pygazelle/sync.py`
- Create: `tests/test_sync.py`

- [ ] **Step 10.1: Write sync wrapper tests**

`tests/test_sync.py`:

```python
import asyncio
import threading
import httpx
from pygazelle.sync import GazelleSyncClient, OrpheusClientSync, RedactedClientSync
from pygazelle.client import GazelleClient
from pygazelle.transport import GazelleTransport
from pygazelle.models import User


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, response_json: dict) -> None:
        self._json = response_json

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=self._json)


def make_sync_client(response_json: dict) -> GazelleSyncClient:
    http = httpx.AsyncClient(transport=MockTransport(response_json))
    transport = GazelleTransport("https://example.com", api_key="k", _http_client=http)
    return GazelleSyncClient(GazelleClient(transport))


def test_sync_client_returns_result_without_await():
    client = make_sync_client({
        "status": "success",
        "response": {
            "id": 1, "username": "user",
            "userstats": {"uploaded": 100, "downloaded": 50, "ratio": 2.0, "requiredRatio": 0.6},
        },
    })
    user = client.user.me()
    assert isinstance(user, User)
    assert user.username == "user"


def test_sync_client_background_thread_is_daemon():
    client = make_sync_client({"status": "success", "response": {}})
    assert client._bg._thread.daemon is True


def test_orpheus_client_sync_wraps_orpheus_client():
    client = OrpheusClientSync(api_key="k")
    assert "orpheus.network" in client._async._transport._ajax_url


def test_redacted_client_sync_wraps_redacted_client():
    client = RedactedClientSync(api_key="k")
    assert "redacted.ch" in client._async._transport._ajax_url


def test_sync_client_reuses_connection_across_calls():
    # With a persistent loop, the httpx client is reused — no reconnect per call.
    # We verify this by making multiple calls and checking no exception is raised.
    client = make_sync_client({
        "status": "success",
        "response": {"id": 1, "username": "u",
                     "userstats": {"uploaded": 0, "downloaded": 0, "ratio": 0.0, "requiredRatio": 0.0}},
    })
    for _ in range(3):
        user = client.user.me()
        assert isinstance(user, User)
```

- [ ] **Step 10.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_sync.py -v
```

Expected: `ImportError` — `sync.py` is empty.

- [ ] **Step 10.3: Implement sync.py**

`src/pygazelle/sync.py`:

```python
from __future__ import annotations

import asyncio
import threading

from .client import GazelleClient, OrpheusClient, RedactedClient


class _BackgroundLoop:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._started = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._started.wait()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()

    def run(self, coro: object) -> object:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type]
        return future.result()


class _SyncProxy:
    """Wraps a resource object, making every async method callable synchronously."""

    def __init__(self, resource: object, loop: _BackgroundLoop) -> None:
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_loop", loop)

    def __getattr__(self, name: str) -> object:
        resource = object.__getattribute__(self, "_resource")
        loop = object.__getattribute__(self, "_loop")
        attr = getattr(resource, name)
        if asyncio.iscoroutinefunction(attr):
            def sync_method(*args: object, **kwargs: object) -> object:
                return loop.run(attr(*args, **kwargs))
            return sync_method
        return attr


class GazelleSyncClient:
    def __init__(self, async_client: GazelleClient) -> None:
        self._async = async_client
        self._bg = _BackgroundLoop()

    @property
    def torrents(self) -> _SyncProxy:
        return _SyncProxy(self._async.torrents, self._bg)

    @property
    def artists(self) -> _SyncProxy:
        return _SyncProxy(self._async.artists, self._bg)

    @property
    def requests(self) -> _SyncProxy:
        return _SyncProxy(self._async.requests, self._bg)

    @property
    def collages(self) -> _SyncProxy:
        return _SyncProxy(self._async.collages, self._bg)

    @property
    def user(self) -> _SyncProxy:
        return _SyncProxy(self._async.user, self._bg)

    @property
    def inbox(self) -> _SyncProxy:
        return _SyncProxy(self._async.inbox, self._bg)

    @property
    def notifications(self) -> _SyncProxy:
        return _SyncProxy(self._async.notifications, self._bg)

    def close(self) -> None:
        self._bg.run(self._async.aclose())


class OrpheusClientSync(GazelleSyncClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(OrpheusClient(username=username, password=password, api_key=api_key, **kwargs))


class RedactedClientSync(GazelleSyncClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(RedactedClient(username=username, password=password, api_key=api_key, **kwargs))
```

- [ ] **Step 10.4: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: all pass.

- [ ] **Step 10.5: Commit**

```bash
git add src/pygazelle/sync.py tests/test_sync.py
git commit -m "feat: add sync wrapper with persistent background event loop"
```

---

## Task 11: API Fixtures & Model Tests

**Files:**
- Create: `tests/fixtures/orpheus/*.json`
- Create: `tests/fixtures/redacted/*.json`
- Create: `tests/models/conftest.py`
- Create: `tests/models/test_torrents.py`
- Create: `tests/models/test_artists.py`
- Create: `tests/models/test_user.py`
- Create: `tests/models/test_notifications.py`

This task requires real API credentials. Set up your `.env` file first:

```
ORPHEUS_API_KEY=your_key_here
REDACTED_API_KEY=your_key_here
```

- [ ] **Step 11.1: Write fixture capture script**

Create `devtools/capture_fixtures.py`:

```python
"""Capture real API response fixtures for model testing. Run once with valid credentials."""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


async def capture(tracker: str, base_url: str, api_key: str) -> None:
    from pygazelle.transport import GazelleTransport

    out = FIXTURE_DIR / tracker
    out.mkdir(parents=True, exist_ok=True)

    async with GazelleTransport(base_url, api_key=api_key, rate=1.0) as t:
        index = await t.request("index")
        (out / "index.json").write_text(json.dumps({"status": "success", "response": index}, indent=2))
        print(f"[{tracker}] Captured index")

        notifications = await t.request("notifications")
        (out / "notifications.json").write_text(json.dumps({"status": "success", "response": notifications}, indent=2))
        print(f"[{tracker}] Captured notifications")

        # Get a torrent ID from a search to fetch as fixture
        browse = await t.request("browse", searchstr="", format="FLAC", page=1)
        results = browse.get("results", [])
        if results and results[0].get("torrents"):
            torrent_id = results[0]["torrents"][0]["torrentId"]
            torrent = await t.request("torrent", id=torrent_id)
            (out / "torrent.json").write_text(json.dumps({"status": "success", "response": torrent}, indent=2))
            print(f"[{tracker}] Captured torrent {torrent_id}")

        # Get an artist fixture
        if results:
            artist_data = results[0].get("artists")
            if artist_data:
                artist_id = artist_data[0]["id"] if isinstance(artist_data, list) else None
                if artist_id:
                    artist = await t.request("artist", id=artist_id)
                    (out / "artist.json").write_text(json.dumps({"status": "success", "response": artist}, indent=2))
                    print(f"[{tracker}] Captured artist {artist_id}")


async def main() -> None:
    orpheus_key = os.getenv("ORPHEUS_API_KEY")
    redacted_key = os.getenv("REDACTED_API_KEY")
    if orpheus_key:
        await capture("orpheus", "https://orpheus.network", orpheus_key)
    if redacted_key:
        await capture("redacted", "https://redacted.ch", redacted_key)
    print("Done.")


asyncio.run(main())
```

- [ ] **Step 11.2: Run the fixture capture script**

```bash
uv run python devtools/capture_fixtures.py
```

Expected: JSON files written to `tests/fixtures/orpheus/` and `tests/fixtures/redacted/`.

- [ ] **Step 11.3: Write model fixture test helpers**

`tests/models/conftest.py`:

```python
import json
from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(tracker: str, name: str) -> dict:
    path = FIXTURE_DIR / tracker / f"{name}.json"
    if not path.exists():
        pytest.skip(f"Fixture {tracker}/{name}.json not captured yet")
    data = json.loads(path.read_text())
    return data["response"]


@pytest.fixture
def orpheus_torrent():
    return load_fixture("orpheus", "torrent")


@pytest.fixture
def redacted_torrent():
    return load_fixture("redacted", "torrent")


@pytest.fixture
def orpheus_artist():
    return load_fixture("orpheus", "artist")


@pytest.fixture
def orpheus_index():
    return load_fixture("orpheus", "index")


@pytest.fixture
def orpheus_notifications():
    return load_fixture("orpheus", "notifications")
```

- [ ] **Step 11.4: Write model fixture tests**

`tests/models/test_torrents.py`:

```python
from pygazelle.models.torrents import Torrent


def test_torrent_model_parses_orpheus_fixture(orpheus_torrent):
    torrent = Torrent.model_validate(orpheus_torrent["torrent"])
    assert isinstance(torrent.id, int)
    assert isinstance(torrent.format, str)
    assert isinstance(torrent.size, int)


def test_torrent_model_parses_redacted_fixture(redacted_torrent):
    torrent = Torrent.model_validate(redacted_torrent["torrent"])
    assert isinstance(torrent.id, int)
    assert isinstance(torrent.format, str)
```

`tests/models/test_artists.py`:

```python
from pygazelle.models.artists import Artist


def test_artist_model_parses_orpheus_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert isinstance(artist.id, int)
    assert isinstance(artist.name, str)
```

`tests/models/test_user.py`:

```python
from pygazelle.models.user import User


def test_user_model_parses_orpheus_index(orpheus_index):
    user = User.model_validate(orpheus_index)
    assert isinstance(user.id, int)
    assert isinstance(user.username, str)
```

`tests/models/test_notifications.py`:

```python
from pygazelle.models.notifications import Notification


def test_notifications_model_parses_orpheus_fixture(orpheus_notifications):
    results = orpheus_notifications.get("results", [])
    if not results:
        return  # no notifications on this account — skip silently
    notification = Notification.model_validate(results[0])
    assert isinstance(notification.torrent_id, int)
```

- [ ] **Step 11.5: Run model tests**

```bash
uv run pytest tests/models/ -v
```

Expected: all pass (or skip if fixture not captured).

- [ ] **Step 11.6: Fix any model field mismatches revealed by fixtures**

If a test fails with a `ValidationError`, the fixture revealed a field name or type mismatch. Update the relevant model in `src/pygazelle/models/` to match. Re-run until all pass.

- [ ] **Step 11.7: Commit**

```bash
git add devtools/capture_fixtures.py tests/fixtures/ tests/models/
git commit -m "feat: add API response fixtures and model validation tests"
```

---

## Task 12: Integration Tests

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_orpheus.py`
- Create: `tests/integration/test_redacted.py`

- [ ] **Step 12.1: Set up root conftest.py**

`tests/conftest.py`:

```python
from dotenv import load_dotenv

load_dotenv()
```

- [ ] **Step 12.2: Set up integration conftest.py**

`tests/integration/conftest.py`:

```python
import os
import pytest


def _skip_if_missing(*var_names: str) -> None:
    missing = [v for v in var_names if not os.getenv(v)]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")


@pytest.fixture
def orpheus_api_key() -> str:
    _skip_if_missing("ORPHEUS_API_KEY")
    return os.environ["ORPHEUS_API_KEY"]


@pytest.fixture
def orpheus_credentials() -> tuple[str, str]:
    _skip_if_missing("ORPHEUS_USERNAME", "ORPHEUS_PASSWORD")
    return os.environ["ORPHEUS_USERNAME"], os.environ["ORPHEUS_PASSWORD"]


@pytest.fixture
def redacted_api_key() -> str:
    _skip_if_missing("REDACTED_API_KEY")
    return os.environ["REDACTED_API_KEY"]


@pytest.fixture
def redacted_credentials() -> tuple[str, str]:
    _skip_if_missing("REDACTED_USERNAME", "REDACTED_PASSWORD")
    return os.environ["REDACTED_USERNAME"], os.environ["REDACTED_PASSWORD"]
```

- [ ] **Step 12.3: Write Orpheus integration tests**

`tests/integration/test_orpheus.py`:

```python
import pytest
from pygazelle.client import OrpheusClient
from pygazelle.models import User, Notification


async def test_orpheus_api_key_auth_returns_user(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key) as client:
        user = await client.user.me()
    assert isinstance(user, User)
    assert isinstance(user.id, int)
    assert isinstance(user.username, str)


async def test_orpheus_cookie_auth_returns_user(orpheus_credentials):
    username, password = orpheus_credentials
    async with OrpheusClient(username=username, password=password) as client:
        user = await client.user.me()
    assert isinstance(user, User)
    assert isinstance(user.username, str)


async def test_orpheus_notifications_list(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key) as client:
        notifications = await client.notifications.list()
    assert isinstance(notifications, list)
    for n in notifications:
        assert isinstance(n, Notification)


async def test_orpheus_torrent_search_returns_results(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key) as client:
        results = await client.torrents.search("", format="FLAC")
    assert isinstance(results, list)
    assert len(results) > 0
```

- [ ] **Step 12.4: Write Redacted integration tests**

`tests/integration/test_redacted.py`:

```python
import pytest
from pygazelle.client import RedactedClient
from pygazelle.models import User, Notification


async def test_redacted_api_key_auth_returns_user(redacted_api_key):
    async with RedactedClient(api_key=redacted_api_key) as client:
        user = await client.user.me()
    assert isinstance(user, User)
    assert isinstance(user.id, int)


async def test_redacted_cookie_auth_returns_user(redacted_credentials):
    username, password = redacted_credentials
    async with RedactedClient(username=username, password=password) as client:
        user = await client.user.me()
    assert isinstance(user, User)


async def test_redacted_notifications_list(redacted_api_key):
    async with RedactedClient(api_key=redacted_api_key) as client:
        notifications = await client.notifications.list()
    assert isinstance(notifications, list)


async def test_redacted_torrent_search_returns_results(redacted_api_key):
    async with RedactedClient(api_key=redacted_api_key) as client:
        results = await client.torrents.search("", format="FLAC")
    assert isinstance(results, list)
    assert len(results) > 0
```

- [ ] **Step 12.5: Run unit tests to confirm no regressions**

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

Expected: all pass.

- [ ] **Step 12.6: Run integration tests**

```bash
uv run pytest tests/integration/ -v
```

Expected: pass (or skip if credentials not in `.env`).

- [ ] **Step 12.7: Update __init__.py public exports**

`src/pygazelle/__init__.py`:

```python
from .client import GazelleClient, OrpheusClient, RedactedClient
from .errors import GazelleAPIError, GazelleAuthError, GazelleError, GazelleNotFoundError, GazelleRateLimitError
from .sync import GazelleSyncClient, OrpheusClientSync, RedactedClientSync

__all__ = [
    "GazelleClient", "OrpheusClient", "RedactedClient",
    "GazelleSyncClient", "OrpheusClientSync", "RedactedClientSync",
    "GazelleError", "GazelleAuthError", "GazelleRateLimitError",
    "GazelleNotFoundError", "GazelleAPIError",
]
```

- [ ] **Step 12.8: Final commit**

```bash
git add tests/conftest.py tests/integration/ src/pygazelle/__init__.py
git commit -m "feat: add integration tests and finalize public API exports"
```
