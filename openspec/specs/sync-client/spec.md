# Capability: sync-client

## Purpose

The sync client wraps the async client to provide a synchronous interface suitable for scripts, notebooks, and environments where `await` is unavailable or undesirable. It drives the async client via a persistent background event loop running in a daemon thread, ensuring connection-pool reuse and compatibility with environments that already have a running event loop (e.g., Jupyter). Tracker-specific sync subclasses (`OrpheusClientSync`, `RedactedClientSync`) mirror their async counterparts.

## Requirements

### Requirement: Sync wrapper with identical API surface
The sync client SHALL expose the same resource namespaces and method signatures as the async client, without requiring `await`.

#### Scenario: Sync call returns result directly
- **WHEN** a sync client resource method is called
- **THEN** the result is returned directly without `await`

#### Scenario: API surface parity
- **WHEN** a method exists on the async client
- **THEN** an equivalent method with the same signature (minus `async`) exists on the sync client

### Requirement: Persistent background event loop
The sync client SHALL use a single background thread with a persistent event loop to drive the async client, not a new event loop per call.

#### Scenario: Connection pool reused across calls
- **WHEN** multiple sync calls are made sequentially
- **THEN** the same underlying httpx connection pool is used (no reconnect per call)

#### Scenario: Works inside running event loop
- **WHEN** the sync client is used inside an environment with an already-running event loop (e.g., Jupyter)
- **THEN** no "event loop already running" error is raised

### Requirement: Tracker-specific sync subclasses
The library SHALL provide `OrpheusClientSync` and `RedactedClientSync` wrapping their respective async clients.

#### Scenario: OrpheusClientSync wraps OrpheusClient
- **WHEN** `OrpheusClientSync` is instantiated
- **THEN** it drives an `OrpheusClient` instance via the background event loop

#### Scenario: RedactedClientSync wraps RedactedClient
- **WHEN** `RedactedClientSync` is instantiated
- **THEN** it drives a `RedactedClient` instance via the background event loop

### Requirement: Background thread is a daemon thread
The background event loop thread SHALL be a daemon thread so it does not prevent process exit.

#### Scenario: Process exits cleanly
- **WHEN** the main thread exits without explicitly closing the sync client
- **THEN** the background thread does not prevent the process from terminating
