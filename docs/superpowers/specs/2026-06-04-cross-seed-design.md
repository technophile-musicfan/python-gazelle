# Cross-Seed — Design

- **Date:** 2026-06-04
- **Epic:** python-gazelle-7gj ([Epic] Cross-Seed)
- **Sub-issues:** python-gazelle-hs3 (API metadata matching), python-gazelle-xx0 (file-list verification & .torrent generation)
- **Status:** Design approved, pending spec review

## Summary

Given a release the user already has on one Gazelle tracker, find the **same
release** on a second Gazelle tracker and return that tracker's `.torrent` so the
user can cross-seed it (add to a torrent client, reusing existing local data).

The flow is **API-only** — it never touches the local filesystem and never
generates a `.torrent` from scratch. It reads the source release's file list and
metadata from the origin tracker's API, searches the target tracker by metadata,
confirms an exact file-list match against a candidate, then downloads the
matched candidate's `.torrent` via the existing download endpoint.

Final byte-level verification is delegated to the user's torrent client, which
re-hashes the downloaded `.torrent` against local data when it is added. The
library's job is to identify a high-confidence match and hand back its `.torrent`.

## Goals

- From a source torrent id on tracker A, produce tracker B's `.torrent` for the
  same release, ready to add to a client.
- Confirm "same release" with a strict, deterministic file-list comparison.
- Stay safely within tracker rate limits (no per-candidate request storms).
- Expose the metadata-match and file-list-verify stages as independently usable,
  testable functions, with one batteries-included orchestrator on top.
- Work across the two Gazelle trackers (Orpheus, Redacted), honoring their schema
  divergences.

## Non-goals

- No local filesystem scanning or hashing (the client does the final recheck).
- No `.torrent` generation — cross-seeding reuses the target tracker's existing
  `.torrent` plus the user's existing data.
- No piece-level content verification in the library (out of reach without the
  data; the client handles it).
- No torrent-client integration (adding the `.torrent` to a client is the
  caller's job).
- No tolerant/fuzzy file-list matching in this iteration (see Risks — strict only).

## Decisions

### Input contract: source torrent → matched `.torrent`
The caller supplies a source torrent id on an origin client and a target client.
The library fetches the source release's metadata + file list from the origin
tracker's API (no filesystem, no source `.torrent` parsing needed — the Gazelle
`torrent` action already returns both). Chosen over a local-directory input
because it keeps the library filesystem-free and leans on data the API already
provides.

### Strict byte-identical file-list verification
A candidate is a confirmed match only if it has the **identical top-level folder
(`file_path`)** and the **identical sorted list of `(path, size)` pairs** as the
source. Chosen for precision and simplicity over folder-tolerant or size-only
matching. Trade-off: cross-seeds where the target stored a different release
folder name are rejected (see Risks). The client's recheck is the ground truth.

### End-to-end orchestrator returning the `.torrent` bytes
One high-level call runs search → verify → download and returns the matched
candidate plus its `.torrent` bytes (or `None` when there is no confirmed match).
The lower-level stages remain available as standalone functions.

### Module of functions taking explicit clients
Cross-seed spans two clients, so it is not a per-client resource. It lives in a
new module `src/pygazelle/crossseed.py` as plain async/sync functions that take
the clients explicitly. Chosen over a stateful `CrossSeeder` class for
simplicity, testability, and no hidden state.

## Architecture

```
crossseed.cross_seed(source_client, source_torrent_id, target_client)   orchestrator
        │
        ├─ source = source_client.torrents.get(id)        Torrent (.group, .files, .file_path)
        ├─ find_candidates(source, target_client)         metadata search + cheap pre-filter  [hs3]
        │       └─ target_client.torrents.search(...)  ->  candidate Torrents (filelists fetched)
        ├─ verify_match(source, candidate)                strict (path,size) + file_path check  [xx0]
        └─ target_client.torrents.download(match.id)      .torrent bytes
        │
        ▼
   CrossSeedResult { match, torrent_file, source_torrent_id, target_torrent_id, confidence }
```

All building blocks already exist in the library:
- `TorrentResource.get(id) -> Torrent`, with `Torrent.group` (artist/album/year),
  `Torrent.files -> list[TorrentFile{path,size}]`, `Torrent.file_path`,
  `Torrent.format/encoding/media/size/file_count`.
- `TorrentResource.search(query, **params) -> list[TorrentResult]`, whose
  `.torrents` are `BrowseTorrent` rows exposing `torrent_id`, `size`,
  `file_count`, `format`, `encoding`, `media` — the cheap pre-filter fields.
- `TorrentResource.download(id) -> bytes`.

No new model parsing is required; this feature is orchestration + matching logic.

### New code
- `src/pygazelle/crossseed.py`:
  - `CrossSeedResult` (a frozen dataclass — it carries raw `.torrent` bytes and
    is not parsed from the API, so it is not a `GazelleModel`):
    `match: Torrent`, `torrent_file: bytes`, `source_torrent_id: int`,
    `target_torrent_id: int`, `confidence: Literal["exact"]`.
  - `async def find_candidates(source: Torrent, target_client) -> list[Torrent]`
    — **[hs3]** search the target by metadata, pre-filter cheaply, fetch file
    lists for survivors, return candidate `Torrent`s.
  - `def verify_match(source: Torrent, candidate: Torrent) -> bool` — **[xx0]**
    strict file-list comparison.
  - `async def cross_seed(source_client, source_torrent_id, target_client) -> CrossSeedResult | None`
    — orchestrator.
- Synchronous surface: expose a sync entry point consistent with the existing
  `sync.py` pattern (e.g. a `cross_seed` helper runnable on the background loop).
- Export the public names (`cross_seed`, `find_candidates`, `verify_match`,
  `CrossSeedResult`) from `pygazelle.__init__` and update `__all__`.

## Detection mechanism

1. **Fetch source** — `source = await source_client.torrents.get(source_torrent_id)`.
   Pull artist(s) and album from `source.group`, plus `source.format`,
   `source.encoding`, `source.media`, `source.size`, `source.file_count`,
   `source.files`, `source.file_path`. If `source.files` is empty (no file list),
   return `None` with a clear reason — verification is impossible.
2. **Search target** — `await target_client.torrents.search(...)` by artist +
   album (groupname). If artist-scoped search returns nothing, fall back to a
   groupname-only search (cross-tracker artist naming diverges).
3. **Cheap pre-filter** — from each `TorrentResult.torrents` (`BrowseTorrent`)
   row, keep only candidate torrent ids whose `format`, `encoding`, `media`,
   `size`, and `file_count` equal the source's. This is done on search-result
   fields **before** any per-candidate fetch, and is the rate-limit-safety lever.
4. **Verify** — for each surviving candidate id (bounded; see below), fetch
   `await target_client.torrents.get(cand_id)` and apply `verify_match`.
5. **Download first confirmed** — `await target_client.torrents.download(cand_id)`
   → bytes → `CrossSeedResult(confidence="exact", ...)`.
6. **No confirmed candidate** → return `None`.

### `verify_match` rule (strict)
```
verify_match(source, candidate) ==
    source.file_path == candidate.file_path
    AND sorted((f.path, f.size) for f in source.files)
        == sorted((f.path, f.size) for f in candidate.files)
```

### Rate-limit safety
- The cheap pre-filter (step 3) runs entirely on search-result fields, so the
  expensive per-candidate `get` calls (step 4) are issued only for size/format
  matches — normally zero or one.
- The number of candidates deep-checked is capped (constant, e.g. a small N);
  if more survive the pre-filter than the cap, the excess is skipped and a
  `log`/note records the truncation (no silent cap).
- All requests pass through the existing `TokenBucket` + retry/backoff. Auth
  errors are never retried in a loop (ban risk).

## Error handling

- Source torrent missing / no file list → `None` (documented reason), not an
  exception, so batch callers can continue.
- `GazelleNotFoundError` on a candidate `get` → skip that candidate.
- Transient/API errors propagate after the transport's normal retries.
- No confirmed match → `None` (the normal "not found on target" outcome).

## Testing

- **Unit** (mock transport, per the existing `StubTransport`/`CapturingTransport`
  pattern):
  - `verify_match`: exact match passes; differing top folder rejects; one
    differing size rejects; extra/missing file rejects; reordered files still
    match (sorted comparison).
  - `find_candidates`: search results → candidates; pre-filter drops
    wrong-format/encoding/size/file_count rows before any `get`; groupname-only
    fallback when artist search is empty; candidate cap honored.
  - `cross_seed` end-to-end: happy path returns `.torrent` bytes + populated
    `CrossSeedResult`; no search hits → `None`; hits but no file-list match →
    `None`; source without file list → `None`.
  - `CrossSeedResult` shape/fields (constructed correctly by the orchestrator).
- **Sync surface**: a test that the sync entry point returns a result without
  `await`.
- **Integration** (opt-in): a live cross-tracker run needs credentials for
  *both* trackers, so it `pytest.skip`s unless both are present; read-only,
  `max_retries=0`.

## Decomposition (for the planning phase)

One spec / one plan covering the pipeline. The plan implements:
- `find_candidates` + the search/pre-filter → maps to **python-gazelle-hs3**.
- `verify_match` + download + `CrossSeedResult` → maps to **python-gazelle-xx0**.
- `cross_seed` orchestrator + sync surface + exports tie them together.

## Risks & limitations

- **Strict folder matching may reject valid cross-seeds.** Trackers often store a
  different top-level release-folder name for identical content. Accepted for now
  (precision over recall). Mitigation path: a future `tolerant=True` option that
  ignores the top-level folder and compares only the inner `(relative path, size)`
  tree. Out of scope for this iteration.
- **Metadata search divergence.** Artist/album naming differs across trackers;
  the groupname-only fallback reduces but does not eliminate misses. The file-list
  verify keeps precision high regardless of search recall.
- **API-only confidence.** A confirmed match is "same names + sizes," not proven
  byte-identical. The user's torrent client performs the authoritative piece-hash
  recheck on add; the library never claims more than it can verify.

## Beads impact

- **python-gazelle-hs3** → the metadata search + candidate pre-filter
  (`find_candidates`).
- **python-gazelle-xx0** → the strict file-list verify + `.torrent` retrieval +
  `CrossSeedResult` (`verify_match`, download wiring).
- **python-gazelle-7gj** (epic) → satisfied by the orchestrator + sync surface +
  exports tying the two together. (Tasks created after writing-plans per project
  workflow.)
