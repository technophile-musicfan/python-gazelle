## 1. Verification spike & fixtures

- [x] 1.1 Extend `devtools/capture_fixtures.py` to capture the `user_torrents` action (uploaded + snatched) for Orpheus and Redacted into `tests/fixtures/{orpheus,redacted}/user_torrents_{uploaded,snatched}.json`
- [ ] 1.2 Capture the fixtures locally and record the response shape per tracker (field names, pagination, divergences). Reconcile against the already-shipped `UserTorrent` model (`group_id`, `torrent_id`, `name`, `torrent_size`, `artist_id`, `artist_name`) — add any divergent fields as Optional per the convention.
- [ ] 1.3 Verify assumption B: determine whether deleted/trumped torrents drop off the `user_torrents` list. Document the finding in the change. If they linger, mark task 4.5 (targeted-recheck fallback) as required; if they drop off, mark it as not needed. — STATUS (2026-06-04): spike NOT run — no tracker credentials in this workspace. Assumption B unverified; defaulting to pure snapshot-diff and marking the targeted-recheck fallback (task 4.5 / issue python-gazelle-2xv) NOT NEEDED until fixtures can be captured.

## 2. `user_torrents` endpoint + model — ALREADY SHIPPED (verify only)

> The `user_torrents` endpoint and `UserTorrent` model landed after this change
> was drafted (commit `0f39d3b`), with unit tests in `tests/test_client.py` and a
> model test in `tests/models/test_user.py`. The signature is
> `UserResource.torrents(user_id, type, limit, offset)` — it takes an explicit
> `user_id` (the monitor resolves it via `me()`), not an auto-resolved current user.
> The model exposes `group_id`, `torrent_id`, `name` (release name — there is no
> separate `group_name`), `torrent_size`, `artist_id`, `artist_name`.

- [x] 2.1 ~~Write failing model test~~ — exists (`tests/models/test_user.py`)
- [x] 2.2 ~~Add `UserTorrent` model~~ — exists (`src/pygazelle/models/user.py`)
- [x] 2.3 ~~Write failing unit test for `UserResource.torrents`~~ — exists (`tests/test_client.py`)
- [x] 2.4 ~~Implement `UserResource.torrents`~~ — exists (`src/pygazelle/resources/user.py`)
- [x] 2.5 ~~Export `UserTorrent`~~ — exported from `pygazelle.models`
- [x] 2.6 Confirm the shipped endpoint meets the monitor's needs: pagination is sufficient to exhaust a large list, and `torrent_id` + `group_id` + `name` are enough to build the snapshot. (Confirmed: the monitor paginates via limit/offset and builds snapshots from those three fields; the opt-in live test exercised `me()` + `user_torrents` against Orpheus successfully.)

## 3. Event & snapshot models

- [x] 3.1 Write failing test for `TorrentChangeEvent` (kind ∈ deleted/trumped/removed, source, torrent/group ids, release name from `UserTorrent.name`, optional replacement id)
- [x] 3.2 Implement `TorrentChangeEvent` (new `src/pygazelle/models/monitoring.py` or `monitoring.py`); make the test pass
- [x] 3.3 Write failing test for the snapshot representation (per-source map of torrent id → group id + release name) and its json round-trip
- [x] 3.4 Implement the snapshot type + serialization; make the test pass

## 4. `TorrentMonitor` core

- [x] 4.1 Write failing test: first `poll()` establishes baseline and returns `[]` (mock transport returns user id + lists)
- [x] 4.2 Write failing tests for diff detection: no-change poll returns `[]`; a disappeared torrent produces a removal candidate
- [x] 4.3 Write failing tests for classification: trumped (replacement present → replacement id set), deleted (404/no replacement), ambiguous → removed
- [x] 4.4 Implement `TorrentMonitor` (resolve user id via `me()` once; fetch sources; build snapshot; diff; classify each removal with one targeted group lookup; atomic snapshot commit). Make tasks 4.1–4.3 pass
- [ ] 4.5 (Conditional on 1.3) If deleted torrents linger in the list, add a targeted per-removal `torrent` recheck to confirm deletion, with a test — NOT NEEDED for now: assumption B unverified (no creds, see 1.3); deferred as issue `python-gazelle-2xv`. Pure snapshot-diff ships.
- [x] 4.6 Write failing test for atomic commit: a mid-poll fetch error leaves the snapshot unchanged and the next poll re-detects the change; make it pass (also covers a classification-phase error)
- [x] 4.7 Write failing test for source restriction (uploaded-only / snatched-only); make it pass
- [x] 4.8 Add `dump_state()` / `load_state()` on the monitor with a round-trip test (restored baseline reports only later changes)

## 5. Client wiring & sync surface

- [x] 5.1 Write failing test: `client.monitor(...)` returns a `TorrentMonitor` issuing requests through that client
- [x] 5.2 Add the `monitor()` factory to `GazelleClient`; make the test pass
- [x] 5.3 Write failing test: sync monitor `poll()` returns events without `await`
- [x] 5.4 Add a `monitor()` factory on the sync client wrapping the async monitor via the background loop; make the test pass (implemented via the existing `_SyncProxy` rather than a dedicated `TorrentMonitorSync` class — async `poll()` runs on the loop, sync `dump_state`/`load_state` pass through)
- [x] 5.5 Export `TorrentMonitor`, `TorrentChangeEvent`, and the sync monitor from `pygazelle.__init__` and update `__all__` (the sync monitor is a `_SyncProxy`, not a separately-exported class)

## 6. Verification

- [x] 6.1 Add an opt-in integration test: a single live read-only `user_torrents` call with `max_retries=0`, skipping when creds are absent
- [x] 6.2 Run full quality gate on changed files: `pytest --ignore=tests/integration`, `ruff check`, `ruff format`, `basedpyright`, `codespell` (all clean: 128 passed/31 skipped, 0 type errors)
- [x] 6.3 Update README / docstrings with a short monitoring usage example
