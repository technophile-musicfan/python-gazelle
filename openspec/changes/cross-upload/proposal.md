## Why

Users who have a release on one Gazelle tracker have no way, via this library, to
upload it to a second tracker with correct metadata. Doing it by hand means
re-typing metadata into the target's schema, manually checking for duplicates,
and hand-filling the upload form — tedious and error-prone, and uploading the
wrong thing has real consequences on a live tracker.

## What Changes

- Add a `cross-upload` capability built as two phases so the live write is
  isolated and opt-in:
  - `prepare_upload(source_torrent_id, source_client, target_client, *, torrent_file)`
    — read-only: maps the source release's metadata to the target schema
    (best-effort, flagging anything unmappable), runs duplicate detection against
    the target, and returns an `UploadDraft`. **No network write.**
  - `submit_upload(target_client, draft, *, allow_duplicate=False)` — the single
    live write: validates the draft, refuses on an exact duplicate unless
    overridden, then POSTs `action=upload` and returns an `UploadResult`.
- Expose `map_metadata` (mapping) and `duplicate_check` (target dup detection) as
  standalone, independently testable functions.
- Add `UserResource.announce_url()` so the caller can build a target-ready
  `.torrent`; the library treats the supplied `.torrent` as opaque bytes (no
  parsing, no generation).
- Make cross-upload available through the synchronous client surface.

No breaking changes — all additions. Reuses the shipped cross-seed search +
`verify_match` for duplicate detection and the existing transport write path
(`request_write`, already used by `add_log` for multipart).

## Capabilities

### New Capabilities

- `cross-upload`: a two-phase prepare/submit flow to upload a source release to a
  target Gazelle tracker — best-effort metadata schema mapping with review flags
  for unmappable fields, duplicate detection (exact/possible) with an exact-dupe
  submit gate, opaque caller-supplied `.torrent`, target announce-URL retrieval,
  and the live upload submission; on async and sync surfaces.

### Modified Capabilities

<!-- None. Cross-upload reuses existing gazelle-client endpoints (torrent, browse,
     download) and the transport write path without changing their requirements;
     the announce-URL read is introduced as part of the cross-upload capability. -->

## Impact

- **New code:** `src/pygazelle/crossupload.py` (`prepare_upload`, `submit_upload`,
  `map_metadata`, `duplicate_check`, `UploadDraft`, `UploadResult`,
  `DuplicateMatch`, release-type/tag mapping tables); `UserResource.announce_url()`
  in `resources/user.py`; a per-tracker announce host alongside the base URLs in
  the client subclasses; a synchronous entry point in `sync.py`; public exports
  in `__init__.py`.
- **Transport:** the `upload` multipart POST via the existing `request_write`
  (which already supports `files=`); confirm no new write mechanism is needed.
- **Dependencies:** none new.
- **Assumptions to verify during implementation:** the Gazelle `action=upload`
  field names and required-field set per tracker (the biggest unknown); the
  Orpheus↔RED release-type id mapping table; and the source of the announce URL
  (passkey field on the index response + per-tracker announce host).
