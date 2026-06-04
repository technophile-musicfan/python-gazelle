## 1. Models & module skeleton

- [x] 1.1 Create `src/pygazelle/crossupload.py` with `from __future__ import annotations` and the dataclasses: `UploadDraft` (mutable: `form`, `unmapped`, `warnings`, `duplicates`, `torrent_file`, `source_torrent_id`, `target_tracker`), `DuplicateMatch` (frozen: `torrent_id`, `group_id`, `kind` ∈ exact/possible, `name`), `UploadResult` (frozen: `torrent_id`, `group_id`, `url`)
- [x] 1.2 Write a unit test asserting the dataclasses hold their fields

## 2. Announce URL retrieval

- [x] 2.1 Determine the announce-URL source per tracker (passkey on the index response + the Orpheus/Redacted announce hosts); add a per-tracker announce host alongside the base URLs in the client subclasses
- [x] 2.2 Write failing test (mock transport): `UserResource.announce_url()` returns the expected announce URL from the passkey + tracker announce host
- [x] 2.3 Implement `announce_url()` (surface `passkey` from the index parse if needed); make the test pass

## 3. Metadata schema mapping (9m7)

- [x] 3.1 Build the release-type mapping table (Orpheus ↔ Redacted ids) and the target required-field set; document sources
- [x] 3.2 Write failing unit tests for `map_metadata(source, target_tracker)`: direct fields mapped; release-type table hit; release-type miss → unmapped + warning; tag divergence → warning
- [x] 3.3 Implement `map_metadata` returning mapped `fields` + `unmapped` + `warnings`; make tests pass

## 4. Duplicate detection (xn1)

- [x] 4.1 Write failing unit tests (mock transport) for `duplicate_check(source, target_client)`: exact duplicate (via cross-seed `verify_match`), possible duplicate (metadata match only), none
- [x] 4.2 Implement `duplicate_check` reusing the cross-seed search + `verify_match`, returning `list[DuplicateMatch]`; make tests pass

## 5. Prepare orchestrator

- [x] 5.1 Write failing unit tests for `prepare_upload(source_torrent_id, source_client, target_client, *, torrent_file)`: assembles the draft (mapped form + unmapped + warnings + duplicates + opaque torrent bytes) and performs ZERO writes (assert no write call on the target transport); source-not-found raises
- [x] 5.2 Implement `prepare_upload` (get source → `map_metadata` → `duplicate_check` → build `UploadDraft`); make tests pass

## 6. Submit (xn1)

- [x] 6.1 Write failing unit tests for `submit_upload(target_client, draft, *, allow_duplicate=False)`: refuses when a required field is missing from `draft.form` (lists missing); refuses on an exact duplicate unless `allow_duplicate=True`; possible duplicates do not block; happy path issues the multipart `action=upload` POST with the expected fields + `.torrent` file and returns `UploadResult`
- [x] 6.2 Implement `submit_upload` (validate required fields against `draft.form`; apply the exact-duplicate gate; POST `action=upload` multipart via `request_write`); make tests pass
- [x] 6.3 Confirm `request_write` supports the upload multipart shape (it already does for `add_log`); extend only if a gap is found

## 7. Sync surface & exports

- [x] 7.1 Write failing tests: synchronous `prepare_upload`/`submit_upload` entry points return without `await`
- [x] 7.2 Add the sync entry points in `sync.py` (run the async functions on the background loop); make tests pass
- [x] 7.3 Export `prepare_upload`, `submit_upload`, `map_metadata`, `duplicate_check`, `UploadDraft`, `UploadResult`, `DuplicateMatch` (and the sync entry points) from `pygazelle.__init__`; add an exports test

## 8. Verification

- [x] 8.1 SAFETY: confirm no test performs a live upload — `submit_upload` is exercised only against a mock transport. Any opt-in integration test is read-only (`announce_url`/`duplicate_check`), `max_retries=0`, skipping without creds; it MUST NOT call `submit_upload` against a live tracker
- [x] 8.2 Run the full quality gate: `pytest --ignore=tests/integration`, `ruff check`, `ruff format`, `basedpyright` (whole project), `codespell`
- [x] 8.3 Add a README cross-upload example showing the prepare → review → submit flow and the announce-URL helper
