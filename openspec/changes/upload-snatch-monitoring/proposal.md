## Why

Users who upload to or snatch from Gazelle trackers have no way to learn, via
this library, when a torrent they care about is deleted or trumped — so they
cannot react (stop seeding a dead torrent, grab a replacement). This change adds
monitoring for the current user's uploaded and snatched torrents.

## What Changes

- Add a `user_torrents` endpoint to the client so a user's uploaded and snatched
  torrent lists can be fetched (currently no endpoint lists a user's torrents).
- Add a `TorrentMonitor` that auto-discovers the watch list (uploaded + snatched)
  and exposes a stateless `await monitor.poll()` returning typed change events
  (`deleted`, `trumped`, `removed`) since the previous snapshot.
- Detect changes by diffing successive `user_torrents` snapshots and classifying
  each disappearance with a single targeted group lookup — no per-torrent polling
  of the whole list (rate-limit safe).
- Provide opt-in snapshot serialization (`dump_state` / `load_state`) so callers
  can persist baseline state across process restarts.
- Make the monitor available through the synchronous client surface.

No breaking changes — all additions.

## Capabilities

### New Capabilities

- `torrent-monitoring`: auto-discovered watch list of the user's uploaded and
  snatched torrents; stateless `poll()` returning typed deletion/trump/removed
  events via snapshot diffing; serializable state; async and sync surfaces.

### Modified Capabilities

- `gazelle-client`: the user resource gains a method to list the current user's
  torrents by type (uploaded, snatched, …) via the `user_torrents` action, and
  the client exposes a factory for constructing a monitor.

## Impact

- **New code:** `src/pygazelle/monitoring.py` (`TorrentMonitor`), models
  `UserTorrent` and `TorrentChangeEvent` under `src/pygazelle/models/`.
- **Modified code:** `resources/user.py` (new `torrents` method),
  `client.py` (`monitor()` factory), `sync.py` (sync monitor wrapper),
  `__init__.py` (public exports), `devtools/capture_fixtures.py`
  (capture `user_torrents` fixtures).
- **Dependencies:** none new — built on the existing transport, rate limiter,
  and Pydantic models.
- **Assumptions to verify during implementation:** the `user_torrents` action's
  shape per tracker, and whether deleted/trumped torrents drop off the list
  (drives whether a targeted-recheck fallback is needed).
