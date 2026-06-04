## 1. Result model & module skeleton

- [ ] 1.1 Create `src/pygazelle/crossseed.py` with `from __future__ import annotations` and a frozen `CrossSeedResult` dataclass (`match: Torrent`, `torrent_file: bytes`, `source_torrent_id: int`, `target_torrent_id: int`, `confidence: Literal["exact"]`)
- [ ] 1.2 Write a unit test asserting `CrossSeedResult` holds and exposes all fields

## 2. Strict file-list verification (xx0)

- [ ] 2.1 Write failing unit tests for `verify_match(source, candidate)`: identical folder + (path,size) set (any order) passes; differing top-level `file_path` rejects; any differing size/path or missing/extra file rejects; empty source file list rejects
- [ ] 2.2 Implement `verify_match(source: Torrent, candidate: Torrent) -> bool` (compare `file_path` and the sorted `(path, size)` list of `.files`); make tests pass

## 3. Metadata candidate discovery (hs3)

- [ ] 3.1 Write failing unit tests (mock transport) for `find_candidates(source, target_client)`: searches by artist+album; pre-filters out candidates whose format/encoding/media/size/file_count differ before any per-candidate `get`; falls back to groupname-only search when artist search is empty; honors the deep-check cap and logs truncation
- [ ] 3.2 Implement `find_candidates(source: Torrent, target_client) -> list[Torrent]` (search → cheap pre-filter on `BrowseTorrent` rows → fetch file lists for survivors up to the cap); make tests pass

## 4. End-to-end orchestrator

- [ ] 4.1 Write failing unit tests (mock transport) for `cross_seed(source_client, source_torrent_id, target_client)`: happy path returns a `CrossSeedResult` with `.torrent` bytes; no verified candidate returns `None`; source without a file list returns `None`
- [ ] 4.2 Implement `async def cross_seed(...)` (get source → `find_candidates` → first `verify_match` → `download` → build `CrossSeedResult`; else `None`); make tests pass

## 5. Sync surface & exports

- [ ] 5.1 Write failing test: the synchronous cross-seed entry point returns a result without `await`
- [ ] 5.2 Add a synchronous cross-seed entry point consistent with `sync.py` (run the async `cross_seed` on the background loop); make the test pass
- [ ] 5.3 Export `cross_seed`, `find_candidates`, `verify_match`, `CrossSeedResult` (and the sync entry point) from `pygazelle.__init__` and update `__all__`; add an import/exports test

## 6. Verification

- [ ] 6.1 Add an opt-in cross-tracker integration test (read-only, `max_retries=0`) that skips unless BOTH trackers' credentials are present
- [ ] 6.2 Run the full quality gate: `pytest --ignore=tests/integration`, `ruff check`, `ruff format`, `basedpyright` (whole project), `codespell`
- [ ] 6.3 Add a short cross-seed usage example to the README
