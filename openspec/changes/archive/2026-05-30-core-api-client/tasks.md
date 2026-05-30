## 1. Project Setup

- [x] 1.1 Add `httpx` and `pydantic` as runtime dependencies in `pyproject.toml`
- [x] 1.2 Add `python-dotenv` as a dev dependency in `pyproject.toml`
- [x] 1.3 Create module skeleton: `errors.py`, `transport.py`, `client.py`, `sync.py`, `resources/`, `models/`

## 2. Error Hierarchy

- [x] 2.1 Implement `GazelleError` base exception in `errors.py`
- [x] 2.2 Implement `GazelleAuthError`, `GazelleRateLimitError`, `GazelleNotFoundError`, `GazelleAPIError` subclasses

## 3. Transport Layer

- [x] 3.1 Implement `GazelleTransport` with `httpx.AsyncClient` and configurable base URL
- [x] 3.2 Implement cookie/session authentication (login POST, session cookie storage)
- [x] 3.3 Implement API key authentication (header injection)
- [x] 3.4 Implement automatic re-authentication on 401/403 for cookie auth
- [x] 3.5 Implement token-bucket rate limiter (configurable rate, default ~3 req/s)
- [x] 3.6 Implement exponential backoff retry for 429 and 5xx responses
- [x] 3.7 Implement error mapping (non-2xx → typed GazelleError subclass)
- [x] 3.8 Write unit tests for transport (mock httpx transport, no real HTTP)

## 4. Response Models

- [x] 4.1 Implement shared base Pydantic v2 models for torrents, artists, requests, collages, user, inbox, notifications
- [ ] 4.2 Implement tracker-specific model subclasses for fields that diverge between Orpheus and Redacted
- [ ] 4.3 Capture real API response fixtures from Orpheus (read-only endpoints)
- [ ] 4.4 Capture real API response fixtures from Redacted (read-only endpoints)
- [x] 4.5 Write model tests validating each model against its fixture

## 5. Resource Classes

- [x] 5.1 Implement `TorrentResource` (`get`, `search`, `download`)
- [x] 5.2 Implement `ArtistResource` (`get`, `search`)
- [x] 5.3 Implement `RequestResource` (`get`, `search`)
- [x] 5.4 Implement `CollageResource` (`get`)
- [x] 5.5 Implement `UserResource` (`me`)
- [x] 5.6 Implement `InboxResource` (`list`, `get`)
- [x] 5.7 Implement `NotificationResource` (`list`)
- [x] 5.8 Write unit tests for each resource using stubbed transport

## 6. Client Classes

- [x] 6.1 Implement `GazelleClient` composing transport + resource properties
- [x] 6.2 Implement `OrpheusClient(GazelleClient)` with Orpheus base URL and overrides
- [x] 6.3 Implement `RedactedClient(GazelleClient)` with Redacted base URL and overrides

## 7. Sync Wrapper

- [x] 7.1 Implement background daemon thread with persistent event loop
- [x] 7.2 Implement `GazelleSyncClient` wrapping `GazelleClient` via `run_coroutine_threadsafe`
- [x] 7.3 Implement `OrpheusClientSync` and `RedactedClientSync`
- [x] 7.4 Write unit tests for sync wrapper (verify parity with async API)

## 8. Integration Tests

- [x] 8.1 Set up `conftest.py` with `load_dotenv()` and credential fixtures (skip if env vars absent)
- [x] 8.2 Write integration tests for `OrpheusClient` against live Orpheus API (read-only)
- [x] 8.3 Write integration tests for `RedactedClient` against live Redacted API (read-only)
- [x] 8.4 Verify both cookie auth and API key auth paths work in integration tests
