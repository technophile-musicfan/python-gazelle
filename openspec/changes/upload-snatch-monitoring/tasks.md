## 1. Verification spike & fixtures

- [ ] 1.1 Extend `devtools/capture_fixtures.py` to capture the `user_torrents` action (uploaded + snatched) for Orpheus and Redacted into `tests/fixtures/{orpheus,redacted}/user_torrents_{uploaded,snatched}.json`
- [ ] 1.2 Capture the fixtures locally and record the response shape per tracker (field names, pagination, divergences)
- [ ] 1.3 Verify assumption B: determine whether deleted/trumped torrents drop off the `user_torrents` list. Document the finding in the change. If they linger, mark task 4.5 (targeted-recheck fallback) as required; if they drop off, mark it as not needed.

## 2. `user_torrents` endpoint + model

- [ ] 2.1 Write failing model test: `UserTorrent` parses the Orpheus and Redacted `user_torrents` fixtures (id, group id, group name at minimum)
- [ ] 2.2 Add `UserTorrent` model in `src/pygazelle/models/user.py`, making divergent fields Optional/union per the tracker-divergence convention; make the model test pass
- [ ] 2.3 Write failing unit test (mock transport): `UserResource.torrents(type=...)` issues the `user_torrents` action and returns `list[UserTorrent]`, including pagination across multiple pages
- [ ] 2.4 Implement `UserResource.torrents(type, limit, offset)` with pagination; make the test pass
- [ ] 2.5 Export `UserTorrent` from `pygazelle.models` (and `pygazelle` if models are re-exported there)

## 3. Event & snapshot models

- [ ] 3.1 Write failing test for `TorrentChangeEvent` (kind ∈ deleted/trumped/removed, source, torrent/group ids, group name, optional replacement id)
- [ ] 3.2 Implement `TorrentChangeEvent` (new `src/pygazelle/models/monitoring.py` or `monitoring.py`); make the test pass
- [ ] 3.3 Write failing test for the snapshot representation (per-source map of torrent id → group id/name) and its json round-trip
- [ ] 3.4 Implement the snapshot type + serialization; make the test pass

## 4. `TorrentMonitor` core

- [ ] 4.1 Write failing test: first `poll()` establishes baseline and returns `[]` (mock transport returns user id + lists)
- [ ] 4.2 Write failing tests for diff detection: no-change poll returns `[]`; a disappeared torrent produces a removal candidate
- [ ] 4.3 Write failing tests for classification: trumped (replacement present → replacement id set), deleted (404/no replacement), ambiguous → removed
- [ ] 4.4 Implement `TorrentMonitor` (resolve user id via `me()` once; fetch sources; build snapshot; diff; classify each removal with one targeted group lookup; atomic snapshot commit). Make tasks 4.1–4.3 pass
- [ ] 4.5 (Conditional on 1.3) If deleted torrents linger in the list, add a targeted per-removal `torrent` recheck to confirm deletion, with a test
- [ ] 4.6 Write failing test for atomic commit: a mid-poll fetch error leaves the snapshot unchanged and the next poll re-detects the change; make it pass
- [ ] 4.7 Write failing test for source restriction (uploaded-only / snatched-only); make it pass
- [ ] 4.8 Add `dump_state()` / `load_state()` on the monitor with a round-trip test (restored baseline reports only later changes)

## 5. Client wiring & sync surface

- [ ] 5.1 Write failing test: `client.monitor(...)` returns a `TorrentMonitor` issuing requests through that client
- [ ] 5.2 Add the `monitor()` factory to `GazelleClient`; make the test pass
- [ ] 5.3 Write failing test: sync monitor `poll()` returns events without `await`
- [ ] 5.4 Add `TorrentMonitorSync` (and a `monitor()` factory on the sync client) wrapping the async monitor via the background loop; make the test pass
- [ ] 5.5 Export `TorrentMonitor`, `TorrentChangeEvent`, and the sync monitor from `pygazelle.__init__` and update `__all__`

## 6. Verification

- [ ] 6.1 Add an opt-in integration test: a single live read-only `user_torrents` call with `max_retries=0`, skipping when creds are absent
- [ ] 6.2 Run full quality gate on changed files: `pytest --ignore=tests/integration`, `ruff check`, `ruff format`, `basedpyright`, `codespell`
- [ ] 6.3 Update README / docstrings with a short monitoring usage example
