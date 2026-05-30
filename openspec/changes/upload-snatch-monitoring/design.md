## Context

Full brainstorm design: `docs/superpowers/specs/2026-05-30-upload-snatch-monitoring-design.md`.

The library already has an async transport with token-bucket rate limiting,
retry/backoff, a typed error hierarchy, resource namespaces, Pydantic v2 models,
and sync wrappers. There is currently no endpoint that lists a user's torrents,
and no monitoring construct. This change adds both, building entirely on the
existing infrastructure.

Constraint that shapes the design: looping per-torrent requests against a
tracker risks rate-limit bans (a project-wide rule). The detection mechanism
must therefore minimize request volume.

## Goals / Non-Goals

**Goals:**
- Detect deletion and trump of the user's uploaded and snatched torrents.
- Auto-discover the watch list from the tracker (no manual ID bookkeeping).
- A stateless, testable `poll()` API — no library-owned loop, no callbacks.
- Stay well within tracker rate limits.
- Work on both Orpheus and Redacted, honoring schema divergences.

**Non-Goals:**
- No library-run background loop, scheduler, or callback registration.
- No torrent-client integration (reacting to events is the caller's job).
- No snatch-count / popularity tracking on the user's uploads (de-scoped).
- No automatic disk persistence; serialization is offered, storage is the
  caller's choice.

## Decisions

### Stateless `poll()` primitive (vs. background loop / callbacks)
`await monitor.poll()` returns the changes since the previous snapshot; the
caller owns cadence and persistence. Chosen over an async-iterator stream and
over callback registration because it is the simplest to test (no lifecycle,
no hidden threads, no inversion of control) and composes with any scheduler the
caller already has. The original epic wording ("callback/event model") is
superseded — the event *model* remains, the callback *delivery* is dropped.

### Auto-discovered watch list via a new `user_torrents` endpoint
The monitor resolves the current user id once via `user.me()`, then fetches the
uploaded and snatched lists through a new `UserResource.torrents(type, …)`
method wrapping the Gazelle `user_torrents` action. Chosen over requiring the
caller to supply IDs so monitoring is batteries-included and always current. The
endpoint is a standalone, independently useful addition (not buried inside the
monitor).

### Snapshot-diff detection (vs. per-torrent polling)
Each `poll()` re-fetches the uploaded/snatched lists and diffs torrent IDs
against the prior snapshot. Torrents that disappeared are removal candidates.
Per-torrent polling of the whole list was rejected: it scales as O(N) requests
per poll and risks bans on large snatch lists. Diffing costs only the list
pages plus one targeted lookup per *removed* torrent.

### Classification: deleted / trumped / removed
Each removal gets one targeted group lookup. A replacement torrent in the same
group → `trumped` (with `replacement_torrent_id`); group gone or `torrent`
lookup 404 with no replacement → `deleted`; ambiguous → `removed`. Trump
detection is an intentional best-effort heuristic; `removed` is the honest
fallback rather than forcing a wrong label.

### Atomic snapshot commit
The new snapshot is stored only after a full successful fetch + classification.
A mid-poll failure leaves the prior snapshot intact, so the next `poll()` retries
cleanly instead of silently dropping events.

### In-memory snapshot with opt-in serialization
The monitor holds the last snapshot in memory; the first `poll()` establishes a
baseline and returns `[]`. `dump_state()` / `load_state()` expose a
json-serializable snapshot so callers can persist across restarts. Rejected
fully-functional `diff(old, new)` free functions (awkward because trump
classification needs the client) and automatic disk persistence (couples the
library to a storage location).

## Risks / Trade-offs

- **`user_torrents` shape unknown / divergent across trackers** → Capture
  Orpheus and Redacted fixtures first (extend `capture_fixtures.py`); model
  divergent fields as Optional/unions per the existing convention.
- **Deleted torrents may linger in the list, breaking diff-detection** →
  **Verify first.** The plan leads with a spike to confirm whether deleted
  torrents drop off `user_torrents`. If they do, ship pure diff. If they linger,
  add a targeted per-removal `torrent` recheck to confirm deletion. Do not build
  the fallback before data justifies it.
- **Trump heuristic mislabels edge cases** → Emit `removed` when ambiguous; the
  event carries enough context (group id/name) for the caller to inspect.
- **Large watch list → many list pages** → Bounded and rate-limited by the
  existing token bucket; far cheaper than per-torrent polling. Pagination is
  exhausted once per poll.

## Migration Plan

Purely additive; no migration. New public names (`TorrentMonitor`,
`TorrentChangeEvent`, `UserTorrent`, the sync wrapper) are exported from
`pygazelle`. Rollback is removal of the new module/methods — nothing existing
depends on them.

## Open Questions

- Exact `user_torrents` action parameters and pagination semantics per tracker —
  resolved during the fixture-capture spike.
- Whether `removed` (unknown) should remain a distinct event kind or be merged —
  pending user confirmation during spec review; design keeps it distinct.
