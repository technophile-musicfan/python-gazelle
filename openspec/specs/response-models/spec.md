# Capability: response-models

## Purpose

Response models define how raw API JSON is deserialized into typed Python objects. All models use Pydantic v2. Shared base classes capture fields common to both Orpheus and Redacted and absorb divergent schemas with Optional fields and union types, rather than per-tracker subclasses. Real API response fixtures from both trackers are captured and used as model test inputs to ensure correctness against live data.

## Requirements

### Requirement: Pydantic v2 response models
All API responses SHALL be deserialized into Pydantic v2 model instances with full type annotations.

#### Scenario: Response validated on deserialization
- **WHEN** an API response is received
- **THEN** it is parsed into a typed Pydantic model and invalid fields raise a validation error

#### Scenario: Model fields are typed
- **WHEN** a model instance is accessed
- **THEN** all fields have correct Python types (not raw strings or dicts)

### Requirement: Shared base models
Fields common across Orpheus and Redacted SHALL be defined in shared base model classes to avoid duplication.

#### Scenario: Shared fields available on both tracker models
- **WHEN** a model is returned from either `OrpheusClient` or `RedactedClient`
- **THEN** common fields (e.g., torrent ID, name, size) are accessible identically on both

### Requirement: API response fixtures for model tests
Real API response JSON fixtures SHALL be captured from both trackers and used as model test inputs.

#### Scenario: Model parses real fixture without error
- **WHEN** a saved API response fixture is parsed into the corresponding model
- **THEN** no validation errors are raised and all fields are populated

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

