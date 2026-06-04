## Why

Users who have a release on one Gazelle tracker have no way, via this library, to
find the same release on a second tracker and obtain its `.torrent` so they can
cross-seed (seed it on the second tracker reusing their existing local data).
Doing this by hand means manual searching and error-prone file-list comparison.

## What Changes

- Add a `cross-seed` capability: from a source torrent id on an origin client and
  a target client, find the same release on the target tracker and return the
  target's `.torrent`.
- The flow is API-only — it reads the source release's metadata + file list from
  the origin tracker, searches the target by metadata, confirms an exact
  file-list match against a candidate, then downloads the matched `.torrent`. No
  local filesystem access and no `.torrent` generation.
- Expose three units: `find_candidates` (metadata search + cheap pre-filter),
  `verify_match` (strict file-list comparison), and an end-to-end `cross_seed`
  orchestrator returning a `CrossSeedResult` (the matched torrent + `.torrent`
  bytes) or `None`.
- Make cross-seeding available through the synchronous client surface.

No breaking changes — all additions. Built entirely on existing endpoints
(`torrents.get`, `torrents.search`, `torrents.download`) and the already-parsed
`Torrent.files` / `Torrent.file_path`.

## Capabilities

### New Capabilities

- `cross-seed`: given a source torrent on one tracker, find the same release on a
  target tracker via metadata search plus strict file-list verification, and
  return that tracker's `.torrent` ready to add to a client; exposed as
  independent match/verify functions plus an end-to-end orchestrator, on async
  and sync surfaces.

### Modified Capabilities

<!-- None. Cross-seed builds on existing gazelle-client endpoints (torrent,
     browse, download) without changing their requirements. -->

## Impact

- **New code:** `src/pygazelle/crossseed.py` (`cross_seed`, `find_candidates`,
  `verify_match`, `CrossSeedResult`); a synchronous entry point in `sync.py`;
  public exports in `__init__.py`.
- **Dependencies:** none new — built on the existing transport, rate limiter, and
  Pydantic models. Reuses `Torrent.files`/`file_path`/`group`,
  `TorrentResource.search`, and `TorrentResource.download`.
- **Assumptions to verify during implementation:** the metadata fields available
  on search results across both trackers (for the cheap pre-filter), and how
  often identical releases share an identical top-level folder name (drives
  whether the strict matcher's recall is acceptable in practice).
