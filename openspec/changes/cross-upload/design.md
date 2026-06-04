## Context

Full brainstorm design: `docs/superpowers/specs/2026-06-04-cross-upload-design.md`.

The library already exposes `torrents.get` (returns `Torrent` with `.group`
metadata, `.files`, `.file_path`), `torrents.search`, `torrents.download`, the
shipped cross-seed `find_candidates`/`verify_match`, and a transport write path
(`request_write`, POST + authkey + multipart `files=`, used by `add_log`).
Uploading is a consequential live write (it creates a torrent on the target), and
the project rule is to treat live writes with extreme care.

## Goals / Non-Goals

**Goals:**
- Map a source release's metadata onto the target's upload schema, flagging every
  field that can't be confidently mapped for human review.
- Detect duplicates on the target before uploading.
- Isolate the live upload behind an explicit `submit_upload`, gated against
  re-uploading an existing release.
- Expose mapping + duplicate-detection as independent testable units; provide a
  sync surface. Work across Orpheus and Redacted.

**Non-Goals:**
- No `.torrent` generation or parsing (caller builds it; opaque bytes).
- No local filesystem access.
- No heuristic guessing of unmappable fields.
- No live upload in any automated test.
- No editing/trumping existing target torrents.

## Decisions

### Two-phase prepare (read-only) + explicit submit (live write)
`prepare_upload` maps metadata, runs duplicate detection, and validates — no
network write — returning an `UploadDraft`. `submit_upload` is the only function
that writes. Chosen over a one-shot upload so the consequential write is opt-in
and isolated from the safe, testable preparation.

### Caller builds the `.torrent`; library exposes the announce URL
A target upload needs a `.torrent` for the target's announce URL hashing the
user's data, which the library cannot compute without the files. The caller
builds it; the library exposes `target.user.announce_url()` and treats the
supplied `.torrent` as opaque bytes. Rejected: library-side generation (needs
filesystem + bencode/piece-hashing) and deep `.torrent` validation (needs a
bencode decoder; the tracker validates on upload).

### Best-effort metadata mapping, flag the rest
`map_metadata` maps confident fields; low-confidence / unmappable /
target-required-but-absent fields go to `draft.unmapped` + `draft.warnings`,
never guessed, never blocking. The caller resolves gaps by setting `draft.form`.
Rejected: strict (one divergent field blocks everything) and auto-guess (a wrong
guess creates a bad live upload).

### Duplicate detection reuses cross-seed; submit gates on exact dupes
`duplicate_check` searches the target by artist+album (reusing cross-seed) and
classifies hits as `exact` (passes `verify_match`) or `possible` (same
group/metadata). `submit_upload` refuses on an `exact` duplicate unless
`allow_duplicate=True`; `possible` are warnings only.

### Module of functions; mutable draft
Cross-upload spans two clients, so it is a module of functions in
`src/pygazelle/crossupload.py` taking clients explicitly, plus a sync entry point.
`UploadDraft` is a mutable dataclass (the caller fills gaps); `UploadResult` and
`DuplicateMatch` are frozen. `submit_upload` validates `draft.form` against the
target's required-field set (the source of truth; `unmapped` is initial guidance).

### Upload submission via the existing write path
`submit_upload` POSTs `action=upload` as multipart (the `.torrent` bytes + form
fields) through `request_write`, which already supports `files=`.

## Risks / Trade-offs

- **Upload form schema is the biggest unknown** (exact `action=upload` field names
  + required set; Orpheus↔RED divergence; not fully known without API
  docs/fixtures) → Build the field set best-effort and verify against real
  docs/a captured upload form during implementation; the mapping/dup/draft logic
  is testable regardless of eventual field names.
- **Release-type mapping table** must come from real Orpheus/RED ids → missing
  entries become `unmapped` (safe — surfaced for the caller).
- **Announce URL source** (passkey field + per-tracker announce host) → verify
  against real index responses.
- **Live-write danger** → mitigated by the two-phase split, the exact-dupe gate,
  and the mock-only `submit_upload` test rule; the library never uploads without
  an explicit `submit_upload` call.

## Migration Plan

Purely additive; no migration. New public names (`prepare_upload`,
`submit_upload`, `map_metadata`, `duplicate_check`, `UploadDraft`,
`UploadResult`, `DuplicateMatch`, the sync entry points, and
`UserResource.announce_url`) are exported from `pygazelle`. Rollback is removal of
the new module/method.

## Open Questions

- Exact `action=upload` field names and required set per tracker — resolved
  against API docs / a captured upload form during implementation.
- Whether `announce_url()` belongs on the user resource generally (likely yes) or
  is scoped to cross-upload — introduced here on the user resource; reusable.
