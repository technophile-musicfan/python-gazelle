## ADDED Requirements

> Note: the user-torrent listing (`UserResource.torrents(user_id, type)` →
> `list[UserTorrent]`) that earlier drafts proposed here has already shipped and
> is documented in the main `gazelle-client` spec. It is therefore no longer part
> of this delta; only the monitor factory below is net-new.

### Requirement: Monitor factory
The client SHALL expose a factory for constructing a torrent monitor bound to
that client, so callers obtain a monitor without wiring the transport manually.

#### Scenario: Monitor created from client
- **WHEN** the monitor factory on a client instance is called
- **THEN** a monitor is returned that issues its requests through that client
