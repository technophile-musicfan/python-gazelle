## ADDED Requirements

### Requirement: Two-phase prepare and submit
The library SHALL separate cross-upload into a read-only preparation step and an
explicit submission step. The preparation step SHALL perform no write to the
target tracker. The submission step SHALL be the only operation that uploads.

#### Scenario: Prepare performs no write
- **WHEN** the prepare step is awaited for a source torrent and a target client
- **THEN** an upload draft is returned and no write request is sent to the target tracker

#### Scenario: Submit performs the upload
- **WHEN** the submit step is awaited for a valid, complete upload draft
- **THEN** the upload is POSTed to the target tracker and a result identifying the new torrent is returned

### Requirement: Best-effort metadata mapping with review flags
Preparation SHALL map the source release's metadata onto the target tracker's
upload schema, mapping every field it can confidently translate. Fields it cannot
confidently map (including divergent enums and target-required fields absent on
the source) SHALL be recorded as unmapped field names plus human-readable
warnings, and SHALL NOT be guessed. Mapping SHALL be usable as a standalone
function.

#### Scenario: Confident fields are mapped
- **WHEN** the source has fields that translate directly (e.g. artist, album, year, format)
- **THEN** those fields appear in the draft's mapped form

#### Scenario: Unmappable field is flagged, not guessed
- **WHEN** a source field has no confident target equivalent (e.g. a release type with no mapping)
- **THEN** the field name is recorded in the draft's unmapped list with a warning, and is left blank in the form

### Requirement: Duplicate detection on the target
Preparation SHALL search the target tracker for releases matching the source and
classify each match as an exact duplicate (the identical release, by file-list
verification) or a possible duplicate (same release metadata, different
edition/format). The matches SHALL be carried on the draft.

#### Scenario: Exact duplicate detected
- **WHEN** the target already has a release whose file list exactly matches the source
- **THEN** the draft records that match classified as an exact duplicate

#### Scenario: Possible duplicate detected
- **WHEN** the target has a release with matching metadata but no exact file-list match
- **THEN** the draft records that match classified as a possible duplicate

#### Scenario: No duplicates
- **WHEN** the target has no matching release
- **THEN** the draft's duplicate list is empty

### Requirement: Exact-duplicate submit gate
Submission SHALL refuse to upload when an exact duplicate exists on the target,
unless the caller explicitly allows it. Possible duplicates SHALL NOT block
submission.

#### Scenario: Exact duplicate blocks submission
- **WHEN** submission is attempted for a draft that has an exact duplicate and the caller has not allowed duplicates
- **THEN** submission is refused without uploading

#### Scenario: Caller overrides the exact-duplicate gate
- **WHEN** submission is attempted for a draft that has an exact duplicate and the caller explicitly allows duplicates
- **THEN** the upload proceeds

#### Scenario: Possible duplicate does not block
- **WHEN** submission is attempted for a draft that has only possible duplicates
- **THEN** the upload proceeds

### Requirement: Required-field validation before submit
Submission SHALL verify that every field the target requires is present in the
draft's form, using the form as the source of truth (the caller MAY fill
previously-unmapped fields). When a required field is missing, submission SHALL
refuse and identify the missing fields.

#### Scenario: Missing required field refuses submission
- **WHEN** submission is attempted while a target-required field is absent from the draft's form
- **THEN** submission is refused and the missing field(s) are identified, without uploading

#### Scenario: Caller-filled field satisfies validation
- **WHEN** the caller fills a previously-unmapped required field on the draft's form and then submits
- **THEN** validation passes and the upload proceeds

### Requirement: Caller-supplied torrent and announce URL
The library SHALL accept the target `.torrent` as caller-supplied opaque bytes and
SHALL NOT parse or generate `.torrent` files. The library SHALL expose the
target tracker's announce URL so the caller can build a target-ready `.torrent`.

#### Scenario: Torrent attached as opaque bytes
- **WHEN** the caller supplies `.torrent` bytes to preparation
- **THEN** those bytes are carried on the draft and attached to the upload form at submission without being parsed

#### Scenario: Announce URL retrieved
- **WHEN** the caller requests the target tracker's announce URL
- **THEN** the announce URL for that tracker is returned

### Requirement: Synchronous cross-upload surface
Cross-upload SHALL be available through the synchronous client surface, mirroring
the async prepare and submit steps without requiring `await`.

#### Scenario: Sync prepare and submit return directly
- **WHEN** the synchronous cross-upload entry points are called
- **THEN** the draft and the upload result are returned directly without `await`
