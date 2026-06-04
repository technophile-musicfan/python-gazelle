# Cross-Upload — Design

- **Date:** 2026-06-04
- **Epic:** python-gazelle-xg5 ([Epic] Cross-Upload)
- **Sub-issues:** python-gazelle-9m7 (metadata schema mapping), python-gazelle-xn1 (upload submission & duplicate detection)
- **Status:** Design approved, pending spec review

## Summary

Given a release the user already has on one Gazelle tracker, help them upload it
to a second tracker with correct metadata. The feature is split into two phases
so the consequential live write is isolated and opt-in:

1. **`prepare_upload(...)`** — read-only. Fetches the source release's metadata,
   maps it to the target tracker's schema (best-effort, flagging anything it
   can't confidently map), runs duplicate detection against the target, and
   returns an `UploadDraft`. Performs **no network write**.
2. **`submit_upload(...)`** — the single live write. Validates the draft is
   complete, applies a duplicate-safety gate, and POSTs `action=upload` to the
   target tracker, returning the new torrent's id/url.

The caller builds the `.torrent` themselves (the library exposes the target's
announce URL as a convenience; it never parses or generates `.torrent` files —
it attaches the caller-supplied bytes as-is). The library's value is metadata
schema mapping, duplicate detection, validation, and form submission.

## Goals

- Map a source release's metadata onto the target tracker's upload schema,
  surfacing every field that can't be mapped confidently for human review.
- Detect duplicates on the target before uploading.
- Isolate the live upload behind an explicit, separately-invoked `submit_upload`
  with a safety gate against re-uploading an existing release.
- Expose mapping and duplicate-detection as independently testable units, with an
  orchestrating `prepare_upload` on top; provide a synchronous surface.
- Work across Orpheus and Redacted, honoring their schema divergences.

## Non-goals

- No `.torrent` generation or parsing (the caller builds the target `.torrent`;
  the library treats it as opaque bytes).
- No local filesystem access.
- No automatic/heuristic guessing of unmappable fields (best-effort + flag only).
- No live upload in any automated test (see Testing — `submit_upload` is tested
  against a mock transport only).
- No editing/trumping existing target torrents; upload of new releases only.

## Decisions

### Two-phase prepare (safe) + explicit submit (live write)
`prepare_upload` is read-only and fully testable; `submit_upload` is the only
function that writes to the target. Chosen over a one-shot `cross_upload` so the
consequential write is opt-in and clearly separated from preparation, matching
the project's live-API caution. Alternative rejected: one-shot upload (the live
write is less explicitly gated) and prepare-only with no submit (the epic
requires submission).

### Caller builds the `.torrent`; library exposes the announce URL
A valid target upload needs a `.torrent` whose announce URL points to the target
tracker and that hashes the user's data — which the library cannot compute
without the files. The caller builds it (e.g. `mktorrent --announce <url>`); the
library exposes `target.user.announce_url()` as a convenience and treats the
supplied `.torrent` as opaque bytes attached to the upload form. Chosen over
library-side generation (would require filesystem access + bencode/piece-hashing,
breaking the filesystem-free design) and over deep validation of the supplied
`.torrent` (would require a bencode decoder; the caller is responsible for
correctness, and the tracker validates on upload).

### Best-effort metadata mapping, flag the rest for review
`map_metadata` maps fields it is confident about; low-confidence, unmappable, or
target-required-but-absent fields are recorded in `draft.unmapped` (field names)
and `draft.warnings` (human-readable reasons). It never guesses and never blocks.
The caller resolves gaps by setting `draft.form[...]` before submit. Chosen over
strict (a single divergent field would block the whole flow) and auto-guess (a
wrong guess creates a malformed/mis-tagged torrent on a live tracker).

### Duplicate detection reuses the cross-seed search; submit gates on exact dupes
`duplicate_check` searches the target by artist + album (reusing the shipped
cross-seed search) and classifies hits as `exact` (passes cross-seed's
`verify_match` — the identical release is already there) or `possible` (same
group/metadata, different edition/format). `submit_upload` **refuses if an
`exact` duplicate exists unless `allow_duplicate=True`**; `possible` duplicates
are warnings only. This blocks the most common rule violation (re-uploading an
existing release) while allowing a deliberate override.

### Module of functions taking explicit clients
Cross-upload spans two clients, so (like cross-seed) it is a module of functions
in `src/pygazelle/crossupload.py` taking the clients explicitly, plus a sync
entry point. `UploadDraft` is a *mutable* dataclass (the caller fills gaps);
`UploadResult` and `DuplicateMatch` are frozen dataclasses.

## Architecture

```
crossupload.prepare_upload(source_torrent_id, source_client, target_client, *, torrent_file)   read-only
        │
        ├─ source = source_client.torrents.get(source_torrent_id)      metadata + files
        ├─ mapped = map_metadata(source, target_tracker)               best-effort  [9m7]
        ├─ dupes  = duplicate_check(source, target_client)             reuse cross-seed  [xn1]
        └─ -> UploadDraft(form, unmapped, warnings, duplicates, torrent_file, source_torrent_id, target_tracker)

# caller reviews: fills draft.form for any draft.unmapped, inspects draft.duplicates

crossupload.submit_upload(target_client, draft, *, allow_duplicate=False) -> UploadResult   the live write  [xn1]
        ├─ refuse if any REQUIRED target field missing from draft.form
        ├─ refuse if an `exact` duplicate exists and not allow_duplicate
        └─ POST action=upload (multipart: torrent_file + form) via request_write
```

### New code
- `src/pygazelle/crossupload.py`:
  - `map_metadata(source: Torrent, target: TrackerKind) -> MappedForm` — pure mapping; `MappedForm` holds `fields`, `unmapped`, `warnings`. **[9m7]**
  - `async def duplicate_check(source: Torrent, target_client) -> list[DuplicateMatch]` — reuse cross-seed search + `verify_match`. **[xn1]**
  - `async def prepare_upload(source_torrent_id, source_client, target_client, *, torrent_file: bytes) -> UploadDraft` — orchestrator.
  - `async def submit_upload(target_client, draft: UploadDraft, *, allow_duplicate: bool = False) -> UploadResult` — live POST. **[xn1]**
  - Dataclasses: `UploadDraft` (mutable), `DuplicateMatch` (frozen), `UploadResult` (frozen). Optionally a `TrackerKind` literal/enum to select mapping tables.
  - Release-type mapping table(s) and any tag-translation table (module-level data).
- `src/pygazelle/resources/user.py`: `announce_url()` (reads `passkey` from the index + a per-tracker announce host).
- Per-tracker config: an announce host alongside the existing base URLs (`OrpheusClient`/`RedactedClient`).
- `src/pygazelle/transport.py`: confirm/extend `request_write` for the `upload` multipart POST (it already supports `files=`, as `add_log` uses).
- `src/pygazelle/sync.py`: synchronous `prepare_upload_sync` / `submit_upload_sync`.
- `src/pygazelle/__init__.py`: export the public names + dataclasses.

## Metadata mapping detail (9m7)

- **Direct**: artist(s), album/title, year, format, encoding, media, album
  description, release description (BBcode). Format/encoding/media enums are
  near-identical across the two trackers.
- **Table-mapped**: **release type** (Orpheus and RED use different numeric ids →
  explicit mapping table; no entry → `unmapped` + warning). **Tags** (different
  taxonomies → pass through with a warning; table-map known divergences).
- **Unmappable / target-required-but-absent** → `draft.unmapped` (machine-readable
  field names) + `draft.warnings` (reasons). Never guessed.

The **required target field set** lives next to the mapping tables; `submit_upload`
validates `draft.form` against it (so a caller who fills `draft.form` satisfies
submit regardless of the initial `unmapped` list).

## Error handling

- `prepare_upload`: source not found → raises (precondition). Mapping gaps →
  `unmapped`/`warnings`, not errors. A failing duplicate search → recorded as a
  warning; prep still returns a draft.
- `submit_upload`: required field missing from `draft.form` → refuse, listing the
  missing fields. `exact` duplicate present and `allow_duplicate=False` → refuse.
  Upload POST failure → typed `GazelleError` propagated. No auth-error retry loop.

## Testing

- **Unit** (mock transport, existing `StubTransport`/`CapturingTransport` style):
  - `map_metadata`: direct fields mapped; release-type table hit; release-type
    miss → `unmapped` + warning; tag divergence → warning.
  - `duplicate_check`: `exact` (via `verify_match`), `possible` (metadata only),
    none.
  - `prepare_upload`: assembles the draft and performs **zero writes** (assert the
    transport received no write call).
  - `submit_upload`: refuses when a required field is missing from `form`; refuses
    on an `exact` duplicate unless `allow_duplicate=True`; happy path issues the
    multipart `upload` POST with the expected fields + `.torrent` file and returns
    `UploadResult`.
  - `announce_url` construction (passkey + per-tracker announce host).
- **Hard safety rule:** `submit_upload` is exercised **only** against a mock
  transport. No automated test ever performs a real upload — it would create real
  torrents and risk tracker-rule violations. At most an opt-in, read-only test for
  `announce_url` / `duplicate_check`; never a live `submit_upload`.

## Decomposition (for the planning phase)

One spec / one plan covering the pipeline. The plan implements:
- `map_metadata` + mapping tables + required-field set → **python-gazelle-9m7**.
- `duplicate_check` + `submit_upload` + the upload transport + `announce_url` +
  `UploadResult`/`DuplicateMatch` → **python-gazelle-xn1**.
- `prepare_upload` orchestrator + `UploadDraft` + sync surface + exports tie them
  together.

## Risks & limitations

- **Upload form schema is the biggest unknown.** The exact `action=upload` field
  names and the required-field set diverge between Orpheus and RED and are not
  fully known without the tracker API docs/fixtures. The mapping is a best-effort
  starting point; verify the field set against real docs/a captured upload form
  during implementation. The mapping/dup-check/draft logic is fully testable
  regardless of the eventual field names.
- **Release-type mapping table** must be built from real Orpheus/RED release-type
  ids; entries we lack become `unmapped` (safe — surfaced for the caller).
- **Announce URL source** (passkey field on the index response + per-tracker
  announce host) needs verification against real responses.
- **Live-write danger**: mitigated by the two-phase split, the duplicate gate, and
  the mock-only test rule. The library never uploads without an explicit
  `submit_upload` call.

## Beads impact

- **python-gazelle-9m7** → metadata schema mapping (`map_metadata`, tables,
  required-field set).
- **python-gazelle-xn1** → duplicate detection + upload submission
  (`duplicate_check`, `submit_upload`, upload transport, `announce_url`).
- **python-gazelle-xg5** (epic) → satisfied by the `prepare_upload` orchestrator +
  sync surface + exports. (Tasks created after writing-plans per project workflow.)
