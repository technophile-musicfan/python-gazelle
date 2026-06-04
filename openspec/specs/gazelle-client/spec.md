# Capability: gazelle-client

## Purpose

The async Gazelle API client exposes tracker API endpoints via typed resource namespaces. It is the primary interface library users interact with, providing an async-native surface backed by named resources for torrents, artists, requests, collages, users, inbox, notifications, bookmarks, subscriptions, and site-wide reads — including mutating actions (add-tag, add-log, request-fill). Tracker-specific subclasses (`OrpheusClient`, `RedactedClient`) configure the correct base URL automatically.

## Requirements
### Requirement: Resource-based API surface
The client SHALL expose Gazelle API endpoints via named resource namespaces accessible as properties on the client instance.

#### Scenario: Resource namespaces available
- **WHEN** a client is instantiated
- **THEN** `client.torrents`, `client.artists`, `client.requests`, `client.collages`, `client.user`, `client.inbox`, `client.notifications`, `client.bookmarks`, `client.subscriptions`, and `client.site` are all accessible

#### Scenario: Resource method returns typed model
- **WHEN** a resource method is awaited
- **THEN** the result is a Pydantic model instance (or a list of them), not a raw dict

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
The `TorrentResource` SHALL support fetching a single torrent by ID, fetching a torrent group with its editions, searching torrents, downloading a torrent file, and the mutating actions add-tag and add-log.

#### Scenario: Get torrent by ID
- **WHEN** `client.torrents.get(id)` is awaited
- **THEN** a `Torrent` model for that ID is returned

#### Scenario: Get torrent group with editions
- **WHEN** `client.torrents.get_group(group_id)` is awaited
- **THEN** a `TorrentGroup` model containing its editions (`torrents`) is returned

#### Scenario: Search torrents
- **WHEN** `client.torrents.search(query, ...)` is awaited
- **THEN** a list of `TorrentResult` models is returned

#### Scenario: Download torrent file
- **WHEN** `client.torrents.download(id)` is awaited
- **THEN** the raw `.torrent` file bytes are returned

#### Scenario: Add tags to a group
- **WHEN** `client.torrents.add_tag(group_id, tags)` is awaited
- **THEN** the tags are submitted and a `TagAddition` (added/rejected) result is returned

#### Scenario: Add a rip log to a torrent
- **WHEN** `client.torrents.add_log(torrent_id, logfiles)` is awaited
- **THEN** the log file(s) are uploaded and a `LogAddition` result is returned

### Requirement: Artist resource methods
The `ArtistResource` SHALL support fetching an artist by ID (including discography, statistics, and similar artists), searching artists by name, and fetching related artists.

#### Scenario: Get artist by ID
- **WHEN** `client.artists.get(id)` is awaited
- **THEN** an `Artist` model is returned, populated with discography, statistics, and similar_artists when the response includes them

#### Scenario: Search artists
- **WHEN** `client.artists.search(name)` is awaited
- **THEN** a list of `ArtistResult` models is returned

#### Scenario: Get similar artists
- **WHEN** `client.artists.similar(id)` is awaited
- **THEN** a list of `SimilarArtist` models is returned

### Requirement: User, inbox, and notification resources
The client SHALL expose resources for the authenticated user's profile, public user profiles and searches, a user's torrents, inbox messages, and notifications.

#### Scenario: Get current user
- **WHEN** `client.user.me()` is awaited
- **THEN** the authenticated user's `User` model is returned

#### Scenario: Get a user profile by ID
- **WHEN** `client.user.get(user_id)` is awaited
- **THEN** a `UserProfile` model is returned

#### Scenario: Search users
- **WHEN** `client.user.search(query)` is awaited
- **THEN** a list of `UserSearchResult` models is returned

#### Scenario: List a user's torrents
- **WHEN** `client.user.torrents(user_id, type)` is awaited
- **THEN** a list of `UserTorrent` models is returned

#### Scenario: List notifications
- **WHEN** `client.notifications.list()` is awaited
- **THEN** a list of `Notification` models is returned

### Requirement: Request resource methods
The `RequestResource` SHALL support fetching a request by ID, searching requests, and filling a request (a mutating action).

#### Scenario: Get request by ID
- **WHEN** `client.requests.get(id)` is awaited
- **THEN** a `Request` model is returned

#### Scenario: Search requests
- **WHEN** `client.requests.search(query)` is awaited
- **THEN** a list of `RequestResult` models is returned

#### Scenario: Fill a request
- **WHEN** `client.requests.fill(request_id, torrent_id=...)` is awaited
- **THEN** the request is marked filled and a `RequestFill` model is returned

#### Scenario: Fill requires a torrent or link
- **WHEN** `client.requests.fill(request_id)` is called with neither `torrent_id` nor `link`
- **THEN** a `ValueError` is raised before any request is sent

### Requirement: Personal-list resources
The client SHALL expose the authenticated user's bookmarks and forum-thread subscriptions.

#### Scenario: List bookmarked torrents and artists
- **WHEN** `client.bookmarks.torrents()` or `client.bookmarks.artists()` is awaited
- **THEN** the corresponding bookmarked items are returned as typed models

#### Scenario: List subscriptions
- **WHEN** `client.subscriptions.list()` is awaited
- **THEN** a list of `ForumSubscription` models is returned

### Requirement: Site resource
The client SHALL expose site-wide read endpoints via `client.site`.

#### Scenario: Fetch top10
- **WHEN** `client.site.top10(type, limit)` is awaited
- **THEN** a list of `Top10Category` models is returned

#### Scenario: Fetch announcements
- **WHEN** `client.site.announcements()` is awaited
- **THEN** an `Announcements` model (site news plus blog posts) is returned

### Requirement: Monitor factory
The client SHALL expose a factory for constructing a torrent monitor bound to
that client, so callers obtain a monitor without wiring the transport manually.

#### Scenario: Monitor created from client
- **WHEN** the monitor factory on a client instance is called
- **THEN** a monitor is returned that issues its requests through that client

