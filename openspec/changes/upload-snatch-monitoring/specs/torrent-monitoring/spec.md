## ADDED Requirements

### Requirement: Auto-discovered watch list
The monitor SHALL discover the set of torrents to watch from the tracker — the
current user's uploaded and snatched torrents — without the caller supplying
torrent IDs. The caller MAY restrict the watched sources.

#### Scenario: Default watches uploaded and snatched
- **WHEN** a monitor is created without specifying sources
- **THEN** it watches both the user's uploaded and snatched torrents

#### Scenario: Source restriction
- **WHEN** a monitor is created with sources restricted to a single type (e.g. snatched)
- **THEN** only torrents of that type are discovered and watched

#### Scenario: Current user resolved automatically
- **WHEN** the monitor needs the user's torrent lists
- **THEN** it resolves the current user's id from the tracker without the caller providing it

### Requirement: Stateless poll returning change events
The monitor SHALL expose an awaitable `poll()` that returns the list of changes
detected since the previous snapshot. The monitor SHALL NOT run its own loop,
timer, or callbacks; the caller controls cadence.

#### Scenario: First poll establishes a baseline
- **WHEN** `poll()` is awaited for the first time
- **THEN** the current torrent lists are recorded as the baseline and an empty list of events is returned

#### Scenario: No changes between polls
- **WHEN** `poll()` is awaited and no watched torrent has changed since the prior snapshot
- **THEN** an empty list of events is returned

#### Scenario: Change since last snapshot is reported
- **WHEN** a watched torrent disappeared since the prior snapshot
- **THEN** `poll()` returns an event describing that change

### Requirement: Deletion, trump, and removal classification
Each change event SHALL classify a removed torrent as `deleted`, `trumped`, or
`removed` (unknown), and carry the torrent id, source, group id, and release name
(the `UserTorrent.name` field; the API exposes no separate group-name field).
A `trumped` event SHALL include the replacement torrent id.

#### Scenario: Trumped torrent
- **WHEN** a watched torrent is gone but its group contains a replacement torrent
- **THEN** the event kind is `trumped` and the replacement torrent id is populated

#### Scenario: Deleted torrent
- **WHEN** a watched torrent is gone and no replacement exists in its group
- **THEN** the event kind is `deleted`

#### Scenario: Ambiguous removal
- **WHEN** a watched torrent is gone but deletion versus trump cannot be determined
- **THEN** the event kind is `removed`

### Requirement: Rate-limit-safe detection
The monitor SHALL detect changes by diffing successive snapshots of the user's
torrent lists, issuing targeted per-torrent lookups only for torrents that
disappeared — never polling every watched torrent individually each cycle.

#### Scenario: Targeted lookups bounded by removals
- **WHEN** `poll()` detects N removed torrents out of a larger watch list
- **THEN** at most N targeted classification lookups are performed, not one per watched torrent

### Requirement: Atomic snapshot commit
The monitor SHALL update its stored snapshot only after a poll completes its
fetch and classification successfully. A failure mid-poll SHALL leave the prior
snapshot unchanged.

#### Scenario: Failed poll preserves prior snapshot
- **WHEN** `poll()` raises while fetching or classifying
- **THEN** the monitor's stored snapshot is unchanged and a subsequent `poll()` re-detects the same pending changes

### Requirement: Serializable monitor state
The monitor SHALL expose its snapshot as a json-serializable value that can be
saved and later restored, so baseline state survives process restarts. The
library SHALL NOT persist state to disk automatically.

#### Scenario: State round-trips
- **WHEN** a monitor's state is dumped and loaded into a new monitor instance
- **THEN** the new instance treats the restored snapshot as its baseline and reports only changes occurring after it

### Requirement: Synchronous monitor surface
Monitoring SHALL be available through the synchronous client surface, mirroring
the async monitor without requiring `await`.

#### Scenario: Sync poll returns directly
- **WHEN** the sync monitor's `poll()` is called
- **THEN** the change events are returned directly without `await`
