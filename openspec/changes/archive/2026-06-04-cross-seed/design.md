## Context

Full brainstorm design: `docs/superpowers/specs/2026-06-04-cross-seed-design.md`.

The library already exposes, per tracker, `torrents.get(id) -> Torrent` (with
`Torrent.group` metadata, `Torrent.files -> list[TorrentFile{path,size}]`,
`Torrent.file_path`, and `format/encoding/media/size/file_count`),
`torrents.search(...) -> list[TorrentResult]` (whose `.torrents` are
`BrowseTorrent` rows exposing `torrent_id`, `size`, `file_count`, `format`,
`encoding`, `media`), and `torrents.download(id) -> bytes`. Cross-seed therefore
needs no new parsing — it is orchestration plus matching logic spanning two
clients. Project rule: never loop requests against a tracker (ban risk), so the
detection must minimize per-candidate API calls.

## Goals / Non-Goals

**Goals:**
- From a source torrent id on an origin client, produce the target tracker's
  `.torrent` for the same release.
- Confirm "same release" with a strict, deterministic file-list comparison.
- Keep API volume low (no per-candidate request storms).
- Expose the match and verify stages as independent, testable functions, with an
  end-to-end orchestrator on top.
- Work across Orpheus and Redacted, honoring schema divergences.

**Non-Goals:**
- No local filesystem scanning or hashing (the torrent client does the final
  piece-hash recheck on add).
- No `.torrent` generation — cross-seeding reuses the target tracker's existing
  `.torrent` plus the user's existing data.
- No piece-level verification in the library; no torrent-client integration.
- No tolerant/fuzzy file-list matching this iteration (strict only).

## Decisions

### Source torrent → matched `.torrent` (API-only)
The caller passes a source torrent id on an origin client plus a target client.
The source release's metadata and file list are read from the origin tracker's
API (the `torrent` action returns both). Chosen over a local-directory input so
the library stays filesystem-free and leans on data the API already provides.
Alternative rejected: scanning local files — couples the library to the
filesystem and duplicates what the client's recheck does authoritatively.

### Strict byte-identical file-list verification
A candidate matches only if it has the identical top-level folder (`file_path`)
**and** the identical sorted list of `(path, size)` pairs as the source. Chosen
for precision and simplicity over folder-tolerant or size-only matching.
Alternatives rejected: folder-tolerant (more recall, but ambiguous data-path
mapping) and size-only (high false-positive rate). The client's recheck is the
ground truth, so high precision here is the right bias.

### End-to-end orchestrator returning `.torrent` bytes
One call runs search → verify → download and returns a `CrossSeedResult` (matched
`Torrent` + `.torrent` bytes + ids + `confidence="exact"`) or `None`. The
`find_candidates` and `verify_match` stages remain public standalone functions.

### Module of functions taking explicit clients
Cross-seed spans two clients, so it is not a per-client resource. It lives in
`src/pygazelle/crossseed.py` as functions taking the clients explicitly, plus a
sync entry point mirroring `sync.py`. Chosen over a stateful `CrossSeeder` class
for simplicity and testability. `CrossSeedResult` is a frozen dataclass (it
carries raw bytes and is not an API model).

### Cheap pre-filter before per-candidate fetch
Candidates are narrowed using search-result fields (`format`, `encoding`,
`media`, `size`, `file_count`) **before** any per-candidate `torrents.get`, which
is the only call that returns a full file list. This bounds expensive calls to
near-zero in the common case and is the rate-limit-safety mechanism.

## Risks / Trade-offs

- **Strict folder matching may reject valid cross-seeds** (identical content,
  different top-level folder name on the target) → Accepted for now (precision
  over recall). Mitigation path: a future `tolerant=True` option comparing only
  the inner `(relative path, size)` tree. Out of scope here.
- **Cross-tracker metadata divergence** (artist/album naming) → search falls back
  to a groupname-only query when an artist-scoped search returns nothing; the
  file-list verify keeps precision high regardless of search recall.
- **Broad artist → many candidates** → the cheap pre-filter plus a constant cap
  on deep-checked candidates (with a logged note on truncation) keep request
  volume bounded; all calls go through the existing token bucket.
- **API-only confidence** → a confirmed match is "same names + sizes," not proven
  byte-identical; the client's recheck is authoritative. The library never claims
  more than it verifies.

## Migration Plan

Purely additive; no migration. New public names (`cross_seed`, `find_candidates`,
`verify_match`, `CrossSeedResult`, and the sync entry point) are exported from
`pygazelle`. Rollback is removal of the new module — nothing existing depends on
it.

## Open Questions

- Exact search parameters that maximize candidate recall per tracker (artistname
  vs groupname vs combined) — resolved during implementation against real
  responses; the strict verify makes recall, not precision, the only thing at
  stake.
- Whether to expose the candidate cap as a parameter — default to a sensible
  constant; revisit if real usage hits it.
