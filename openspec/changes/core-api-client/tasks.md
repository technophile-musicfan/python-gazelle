## 1. Project Setup

- [ ] 1.1 Add `httpx` and `pydantic` as runtime dependencies in `pyproject.toml`
- [ ] 1.2 Add `python-dotenv` as a dev dependency in `pyproject.toml`
- [ ] 1.3 Create module skeleton: `errors.py`, `transport.py`, `client.py`, `sync.py`, `resources/`, `models/`

## 2. Error Hierarchy

- [ ] 2.1 Implement `GazelleError` base exception in `errors.py`
- [ ] 2.2 Implement `GazelleAuthError`, `GazelleRateLimitError`, `GazelleNotFoundError`, `GazelleAPIError` subclasses

## 3. Transport Layer

- [ ] 3.1 Implement `GazelleTransport` with `httpx.AsyncClient` and configurable base URL
- [ ] 3.2 Implement cookie/session authentication (login POST, session cookie storage)
- [ ] 3.3 Implement API key authentication (header injection)
- [ ] 3.4 Implement automatic re-authentication on 401/403 for cookie auth
- [ ] 3.5 Implement token-bucket rate limiter (configurable rate, default ~3 req/s)
- [ ] 3.6 Implement exponential backoff retry for 429 and 5xx responses
- [ ] 3.7 Implement error mapping (non-2xx → typed GazelleError subclass)
- [ ] 3.8 Write unit tests for transport (mock httpx transport, no real HTTP)

## 4. Response Models

- [ ] 4.1 Implement shared base Pydantic v2 models for torrents, artists, requests, collages, user, inbox, notifications
- [ ] 4.2 Implement tracker-specific model subclasses for fields that diverge between Orpheus and Redacted
- [ ] 4.3 Capture real API response fixtures from Orpheus (read-only endpoints)
- [ ] 4.4 Capture real API response fixtures from Redacted (read-only endpoints)
- [ ] 4.5 Write model tests validating each model against its fixture

## 5. Resource Classes

- [ ] 5.1 Implement `TorrentResource` (`get`, `search`, `download`)
- [ ] 5.2 Implement `ArtistResource` (`get`, `search`)
- [ ] 5.3 Implement `RequestResource` (`get`, `search`)
- [ ] 5.4 Implement `CollageResource` (`get`)
- [ ] 5.5 Implement `UserResource` (`me`)
- [ ] 5.6 Implement `InboxResource` (`list`, `get`)
- [ ] 5.7 Implement `NotificationResource` (`list`)
- [ ] 5.8 Write unit tests for each resource using stubbed transport

## 6. Client Classes

- [ ] 6.1 Implement `GazelleClient` composing transport + resource properties
- [ ] 6.2 Implement `OrpheusClient(GazelleClient)` with Orpheus base URL and overrides
- [ ] 6.3 Implement `RedactedClient(GazelleClient)` with Redacted base URL and overrides

## 7. Sync Wrapper

- [ ] 7.1 Implement background daemon thread with persistent event loop
- [ ] 7.2 Implement `GazelleSyncClient` wrapping `GazelleClient` via `run_coroutine_threadsafe`
- [ ] 7.3 Implement `OrpheusClientSync` and `RedactedClientSync`
- [ ] 7.4 Write unit tests for sync wrapper (verify parity with async API)

## 8. Integration Tests

- [ ] 8.1 Set up `conftest.py` with `load_dotenv()` and credential fixtures (skip if env vars absent)
- [ ] 8.2 Write integration tests for `OrpheusClient` against live Orpheus API (read-only)
- [ ] 8.3 Write integration tests for `RedactedClient` against live Redacted API (read-only)
- [ ] 8.4 Verify both cookie auth and API key auth paths work in integration tests
