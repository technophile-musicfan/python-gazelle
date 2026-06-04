# Capability: cross-seed

## Purpose

Given a release the user already has on one Gazelle tracker, find the same release on a second tracker and return that tracker's `.torrent` so the user can cross-seed it (add to a torrent client, reusing existing local data). The flow is API-only: it reads the source release's metadata and file list from the origin tracker, searches the target tracker by metadata, confirms an exact file-list match against a candidate, then downloads the matched `.torrent`. It generates no `.torrent` and never touches the local filesystem; the user's torrent client performs the authoritative piece-hash recheck when the `.torrent` is added. Exposed as independent discovery/verification functions plus an end-to-end orchestrator, on both async and synchronous surfaces.

## Requirements
### Requirement: Cross-seed a source release to a target tracker
The library SHALL provide an end-to-end operation that, given a source torrent id
on an origin client and a target client, finds the same release on the target
tracker and returns that tracker's `.torrent`. The operation SHALL be available
without the caller wiring the search, verification, or download steps manually.

#### Scenario: Match found end-to-end
- **WHEN** the cross-seed operation is awaited for a source torrent that has an exact-file-list match on the target tracker
- **THEN** a result is returned containing the matched target torrent and its `.torrent` bytes

#### Scenario: No match found
- **WHEN** the cross-seed operation is awaited and no target candidate exactly matches the source file list
- **THEN** no result is returned (a null/None result), without raising

#### Scenario: Source has no file list
- **WHEN** the cross-seed operation is awaited for a source torrent whose file list is empty or unavailable
- **THEN** no result is returned, because verification is impossible

### Requirement: Metadata-based candidate discovery
The library SHALL discover candidate releases on the target tracker by searching
on the source release's metadata (artist and album), and SHALL narrow candidates
using cheap search-result fields (format, encoding, media, size, file count)
before fetching any candidate's full file list. The discovery stage SHALL be
usable as a standalone function.

#### Scenario: Candidates discovered by metadata
- **WHEN** candidate discovery runs for a source release
- **THEN** the target tracker is searched by the source's artist and album and matching candidates are returned

#### Scenario: Wrong-format candidates pre-filtered
- **WHEN** a search returns candidates whose format, encoding, media, size, or file count differ from the source
- **THEN** those candidates are excluded before any per-candidate file-list fetch

#### Scenario: Artist search falls back to groupname
- **WHEN** an artist-scoped search returns no candidates
- **THEN** discovery retries with a groupname-only search

### Requirement: Strict file-list verification
The library SHALL confirm a candidate as a match only when its top-level folder
path is identical to the source's and its set of (file path, file size) pairs is
identical to the source's. The verification SHALL be usable as a standalone
function and SHALL be order-independent for the file list.

#### Scenario: Identical file list confirms a match
- **WHEN** a candidate has the same top-level folder and the same (path, size) pairs as the source, in any order
- **THEN** verification confirms the match

#### Scenario: Differing top-level folder rejects
- **WHEN** a candidate's file contents match but its top-level folder name differs from the source's
- **THEN** verification rejects the candidate

#### Scenario: Any size or path difference rejects
- **WHEN** a candidate differs from the source in any file path, file size, or in the set of files present
- **THEN** verification rejects the candidate

### Requirement: Cross-seed result contents
A cross-seed result SHALL carry the matched target torrent, the downloaded
`.torrent` bytes, the source and target torrent ids, and a confidence indicator.

#### Scenario: Result exposes match and torrent file
- **WHEN** a cross-seed match is returned
- **THEN** the result exposes the matched torrent, its `.torrent` bytes, the source and target torrent ids, and a confidence value of `exact`

### Requirement: Rate-limit-safe candidate evaluation
The library SHALL minimize requests against the target tracker: it SHALL apply
the cheap metadata pre-filter before fetching any candidate's file list, and it
SHALL bound the number of candidates whose file lists are fetched. When the bound
truncates evaluation, the library SHALL record that truncation rather than
silently dropping candidates.

#### Scenario: Per-candidate fetches bounded by pre-filter
- **WHEN** a search returns many candidates but only a few survive the cheap metadata pre-filter
- **THEN** full file lists are fetched only for the survivors, not for every search result

#### Scenario: Truncation is reported
- **WHEN** more candidates survive the pre-filter than the evaluation cap allows
- **THEN** the excess is skipped and the truncation is logged, not silently ignored

### Requirement: Synchronous cross-seed surface
Cross-seeding SHALL be available through the synchronous client surface,
mirroring the async operation without requiring `await`.

#### Scenario: Sync cross-seed returns directly
- **WHEN** the synchronous cross-seed entry point is called
- **THEN** the result (or null result) is returned directly without `await`
