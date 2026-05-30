## ADDED Requirements

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

### Requirement: Tracker-specific model variants
Where Orpheus and Redacted return divergent schemas, tracker-specific model subclasses SHALL be used.

#### Scenario: Tracker-specific fields accessible
- **WHEN** a model is returned from `OrpheusClient`
- **THEN** Orpheus-specific fields are accessible and correctly typed

### Requirement: API response fixtures for model tests
Real API response JSON fixtures SHALL be captured from both trackers and used as model test inputs.

#### Scenario: Model parses real fixture without error
- **WHEN** a saved API response fixture is parsed into the corresponding model
- **THEN** no validation errors are raised and all fields are populated
