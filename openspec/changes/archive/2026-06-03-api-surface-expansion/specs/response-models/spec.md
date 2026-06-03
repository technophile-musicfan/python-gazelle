## REMOVED Requirements

### Requirement: Tracker-specific model variants
**Reason**: The implemented design does not use per-tracker subclasses. Orpheus/RED schema divergences are absorbed into shared base models via Optional fields and union types, because resources build the same base model regardless of tracker and the model tests validate both trackers' fixtures against that single base class. Per-tracker subclasses would be dead code. Replaced by "Tolerant base models for tracker divergence".

## ADDED Requirements

### Requirement: Tolerant base models for tracker divergence
Where Orpheus and Redacted return divergent schemas for the same action, the shared base model SHALL absorb the divergence using Optional fields and union types, rather than per-tracker subclasses.

#### Scenario: Field absent on one tracker
- **WHEN** one tracker omits a field that the other includes
- **THEN** the base model declares it Optional, parsing succeeds for both, and the field is `None` where absent

#### Scenario: Field shape differs across trackers
- **WHEN** the trackers return different types or shapes for the same field (e.g. a freeleech flag as a bool on one tracker and a string enum on the other)
- **THEN** the base model declares a union type that accepts both forms

### Requirement: Endpoint model coverage
Every implemented read and write endpoint SHALL deserialize its response into typed models covering the documented response fields.

#### Scenario: New endpoints have models
- **WHEN** an endpoint such as top10, announcements, bookmarks, subscriptions, a user profile, an artist discography, or a write action is awaited
- **THEN** its response is returned as a typed model (for example `Top10Category`, `Announcements`, `ForumSubscription`, `UserProfile`, `ArtistTorrentGroup`, or `TagAddition`)
