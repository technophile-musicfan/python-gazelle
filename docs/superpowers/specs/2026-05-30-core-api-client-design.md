# Core API Client — Design Spec

**Date:** 2026-05-30
**Epic:** python-gazelle-ahf

## Overview

A layered Python client library for Gazelle-based music trackers. Async-native internally (httpx), with a sync wrapper backed by a persistent event loop thread. Resource-based API surface. Pydantic v2 response models. Tracker-specific subclasses for Orpheus and Redacted.

---

## Architecture

Three layers, each independently testable:

```
┌─────────────────────────────────┐
│  Sync wrapper (asyncio bridge)  │  GazelleSyncClient
├─────────────────────────────────┤
│  Domain layer (resources)       │  GazelleClient → OrpheusClient / RedactedClient
│    .torrents  .artists  .user   │  resource objects returning Pydantic models
├─────────────────────────────────┤
│  Transport layer                │  GazelleTransport
│    auth · rate limiting · retry │  wraps httpx.AsyncClient
└─────────────────────────────────┘
```

---

## Transport Layer

`GazelleTransport` wraps `httpx.AsyncClient` and owns all HTTP concerns.

### Authentication

Two modes, configured at instantiation:

- **Cookie/session** — POST login with username + password, store session cookie. Re-authenticate automatically on 401/403.
- **API key** — set as a request header. Used where the tracker supports it.

Integration tests support both via env vars:
- Cookie: `ORPHEUS_USERNAME` / `ORPHEUS_PASSWORD`, `REDACTED_USERNAME` / `REDACTED_PASSWORD`
- API key: `ORPHEUS_API_KEY`, `REDACTED_API_KEY`

### Rate Limiting

Token bucket per client instance. Default ~3 req/s (conservative; configurable). Requests wait for an available token before firing.

### Retry

Exponential backoff on:
- `429` — rate limited by server (after local token bucket)
- `5xx` — transient server errors

Non-retryable responses raised immediately: `400`, `401`, `403`, `404`.

### Base URL

Set at construction time. `OrpheusClient` and `RedactedClient` pass their respective base URLs.

### Error Hierarchy

```
GazelleError
  ├── GazelleAuthError       # 401/403, login failure
  ├── GazelleRateLimitError  # 429 after retries exhausted
  ├── GazelleNotFoundError   # 404
  └── GazelleAPIError        # other non-2xx
```

---

## Domain Layer

### Client Classes

```python
GazelleClient          # base, async-native
  ├── OrpheusClient    # Orpheus base URL, Orpheus-specific overrides
  └── RedactedClient   # Redacted base URL, Redacted-specific overrides
```

Each client exposes resource namespaces as properties:

```python
client.torrents        # TorrentResource
client.artists         # ArtistResource
client.requests        # RequestResource
client.collages        # CollageResource
client.user            # UserResource
client.inbox           # InboxResource
client.notifications   # NotificationResource
```

### Resource Classes

Each resource holds a reference to the transport and returns Pydantic models. Example:

```python
class TorrentResource:
    async def get(self, id: int) -> Torrent: ...
    async def search(self, query: str, ...) -> list[TorrentResult]: ...
    async def download(self, id: int) -> bytes: ...

class ArtistResource:
    async def get(self, id: int) -> Artist: ...
    async def search(self, name: str) -> list[ArtistResult]: ...
```

Tracker subclasses override or extend resource classes where Orpheus and Redacted diverge (endpoint paths, field names, extra endpoints).

### Response Models

Pydantic v2 models. Shared base models where tracker schemas align; tracker-specific submodels where they diverge.

---

## Sync Wrapper

`GazelleSyncClient` (and tracker subclasses `OrpheusClientSync`, `RedactedClientSync`) wrap the async client via a background thread with a persistent event loop:

```python
# Async usage
client = OrpheusClient(api_key="...")
torrent = await client.torrents.get(123)

# Sync usage
client = OrpheusClientSync(api_key="...")
torrent = client.torrents.get(123)
```

The sync wrapper uses `asyncio.run_coroutine_threadsafe()` against a loop running on a dedicated daemon thread. This avoids:
- Per-call event loop creation (breaks connection pooling)
- Conflicts with already-running event loops (e.g., Jupyter)

The sync API mirrors the async API exactly — no duplicated method signatures.

---

## Testing

### Unit Tests
- Transport: rate limiting, retry, auth refresh — tested against a mock `httpx` transport, no real HTTP
- Resources: each method tested with a stubbed transport returning fixture data

### Model Tests
- Pydantic models validated against real API response fixtures (JSON files captured from both trackers)
- Ensures model schemas stay in sync with actual responses

### Integration Tests
- Opt-in via env vars; skipped in CI unless credentials are present
- Support both cookie auth and API key auth
- Hit a small set of read-only endpoints against both Orpheus and Redacted

---

## Module Structure

```
src/pygazelle/
  transport.py       # GazelleTransport, auth, rate limiting, retry
  client.py          # GazelleClient, OrpheusClient, RedactedClient
  sync.py            # GazelleSyncClient, OrpheusClientSync, RedactedClientSync
  errors.py          # GazelleError hierarchy
  resources/
    torrents.py
    artists.py
    requests.py
    collages.py
    user.py
    inbox.py
    notifications.py
  models/
    torrents.py
    artists.py
    requests.py
    collages.py
    user.py
    inbox.py
    notifications.py
```
