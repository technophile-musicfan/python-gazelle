## ADDED Requirements

### Requirement: User torrent listing
The `UserResource` SHALL support listing the current user's torrents by type
(e.g. uploaded, snatched) via the tracker's `user_torrents` action, returning
typed models.

#### Scenario: List uploaded torrents
- **WHEN** the user resource is asked for torrents of type `uploaded`
- **THEN** a list of typed user-torrent models for the current user's uploads is returned

#### Scenario: List snatched torrents
- **WHEN** the user resource is asked for torrents of type `snatched`
- **THEN** a list of typed user-torrent models for the current user's snatches is returned

#### Scenario: Result is typed
- **WHEN** a user-torrent listing is awaited
- **THEN** each result is a Pydantic model instance exposing at least the torrent id, group id, and group name

### Requirement: Monitor factory
The client SHALL expose a factory for constructing a torrent monitor bound to
that client, so callers obtain a monitor without wiring the transport manually.

#### Scenario: Monitor created from client
- **WHEN** the monitor factory on a client instance is called
- **THEN** a monitor is returned that issues its requests through that client
