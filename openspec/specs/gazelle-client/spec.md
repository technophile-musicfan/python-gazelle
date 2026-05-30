# Capability: gazelle-client

## Purpose

The async Gazelle API client exposes tracker API endpoints via typed resource namespaces. It is the primary interface library users interact with, providing an async-native surface backed by named resources for torrents, artists, requests, collages, users, inbox, and notifications. Tracker-specific subclasses (`OrpheusClient`, `RedactedClient`) configure the correct base URL automatically.

## Requirements

### Requirement: Resource-based API surface
The client SHALL expose Gazelle API endpoints via named resource namespaces accessible as properties on the client instance.

#### Scenario: Resource namespaces available
- **WHEN** a client is instantiated
- **THEN** `client.torrents`, `client.artists`, `client.requests`, `client.collages`, `client.user`, `client.inbox`, and `client.notifications` are all accessible

#### Scenario: Resource method returns typed model
- **WHEN** a resource method is awaited
- **THEN** the result is a Pydantic model instance, not a raw dict

### Requirement: Async-native interface
All resource methods SHALL be coroutines requiring `await`.

#### Scenario: Resource method is a coroutine
- **WHEN** a resource method is called without `await`
- **THEN** a coroutine object is returned, not the result

### Requirement: Tracker subclasses
The library SHALL provide `OrpheusClient` and `RedactedClient` subclasses that configure the correct base URL and apply any per-tracker overrides.

#### Scenario: OrpheusClient uses Orpheus base URL
- **WHEN** `OrpheusClient` is instantiated
- **THEN** all requests are sent to the Orpheus API base URL

#### Scenario: RedactedClient uses Redacted base URL
- **WHEN** `RedactedClient` is instantiated
- **THEN** all requests are sent to the Redacted API base URL

### Requirement: Torrent resource methods
The `TorrentResource` SHALL support fetching a torrent by ID, searching torrents, and downloading a torrent file.

#### Scenario: Get torrent by ID
- **WHEN** `client.torrents.get(id)` is awaited
- **THEN** a `Torrent` model for that ID is returned

#### Scenario: Search torrents
- **WHEN** `client.torrents.search(query, ...)` is awaited
- **THEN** a list of `TorrentResult` models is returned

#### Scenario: Download torrent file
- **WHEN** `client.torrents.download(id)` is awaited
- **THEN** the raw `.torrent` file bytes are returned

### Requirement: Artist resource methods
The `ArtistResource` SHALL support fetching an artist by ID and searching artists by name.

#### Scenario: Get artist by ID
- **WHEN** `client.artists.get(id)` is awaited
- **THEN** an `Artist` model is returned

#### Scenario: Search artists
- **WHEN** `client.artists.search(name)` is awaited
- **THEN** a list of `ArtistResult` models is returned

### Requirement: User, inbox, and notification resources
The client SHALL expose resources for the authenticated user's profile, inbox messages, and notifications.

#### Scenario: Get current user
- **WHEN** `client.user.me()` is awaited
- **THEN** the authenticated user's `User` model is returned

#### Scenario: List notifications
- **WHEN** `client.notifications.list()` is awaited
- **THEN** a list of `Notification` models is returned
