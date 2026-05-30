## Why

`python-gazelle` has no implementation yet — just a scaffold. The Core API Client is the foundation everything else (upload monitoring, cross-seed, cross-upload) depends on. Without it, nothing else can be built.

## What Changes

- **New**: `GazelleTransport` — async HTTP transport with cookie/API key auth, token-bucket rate limiting, exponential backoff retry, and a typed error hierarchy
- **New**: `GazelleClient` — async-native base client with resource-based API surface (`client.torrents`, `client.artists`, etc.)
- **New**: `OrpheusClient` / `RedactedClient` — tracker-specific subclasses with correct base URLs and any per-tracker overrides
- **New**: Pydantic v2 response models for all resource types (torrents, artists, requests, collages, user, inbox, notifications)
- **New**: `GazelleSyncClient` / `OrpheusClientSync` / `RedactedClientSync` — sync wrappers backed by async client via persistent background event loop thread
- **New**: Integration test infrastructure with `.env`-based credential loading via `python-dotenv`

## Capabilities

### New Capabilities

- `gazelle-transport`: Async HTTP transport — httpx session, cookie and API key auth, token-bucket rate limiting, exponential backoff retry, typed error hierarchy
- `gazelle-client`: Client hierarchy and resource namespaces — `GazelleClient`, `OrpheusClient`, `RedactedClient`, resource objects (torrents, artists, requests, collages, user, inbox, notifications)
- `response-models`: Pydantic v2 response models for all Gazelle resource types, with shared bases and tracker-specific submodels where schemas diverge
- `sync-client`: Sync wrapper clients (`GazelleSyncClient`, `OrpheusClientSync`, `RedactedClientSync`) backed by async client via background thread with persistent event loop

### Modified Capabilities

## Impact

- Adds `httpx`, `pydantic` as runtime dependencies
- Adds `python-dotenv` as a dev dependency (integration test credential loading)
- Introduces `src/pygazelle/transport.py`, `client.py`, `sync.py`, `errors.py`, `resources/`, `models/`
- All future features (upload monitoring, cross-seed, cross-upload) depend on `gazelle-client` and `gazelle-transport`
