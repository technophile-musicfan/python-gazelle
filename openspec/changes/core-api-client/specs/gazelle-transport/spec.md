## ADDED Requirements

### Requirement: Cookie authentication
The transport SHALL support login via username and password, storing the resulting session cookie and attaching it to all subsequent requests.

#### Scenario: Successful login
- **WHEN** transport is instantiated with username and password
- **THEN** a login POST is performed and the session cookie is stored

#### Scenario: Automatic re-authentication
- **WHEN** a request returns 401 or 403 and cookie auth is configured
- **THEN** the transport re-authenticates and retries the original request

### Requirement: API key authentication
The transport SHALL support authentication via an API key passed as a request header, where the tracker supports it.

#### Scenario: API key attached to requests
- **WHEN** transport is instantiated with an API key
- **THEN** all requests include the API key header and no login POST is performed

### Requirement: Token-bucket rate limiting
The transport SHALL enforce a configurable request rate limit using a token bucket, waiting for an available token before firing each request.

#### Scenario: Rate limit respected
- **WHEN** requests are made faster than the configured rate
- **THEN** excess requests are delayed until a token is available, not rejected

#### Scenario: Configurable rate
- **WHEN** client is instantiated with a custom rate limit
- **THEN** the token bucket uses that rate instead of the default

### Requirement: Retry with exponential backoff
The transport SHALL retry requests on transient errors (429, 5xx) using exponential backoff, up to a configurable maximum number of attempts.

#### Scenario: Retry on 429
- **WHEN** a request receives a 429 response
- **THEN** the transport waits and retries with exponential backoff

#### Scenario: Retry on 5xx
- **WHEN** a request receives a 5xx response
- **THEN** the transport retries with exponential backoff

#### Scenario: No retry on client errors
- **WHEN** a request receives a 400, 401, 403, or 404 response
- **THEN** the transport raises the appropriate error immediately without retrying

### Requirement: Typed error hierarchy
The transport SHALL raise typed exceptions for all error conditions, derived from a common `GazelleError` base.

#### Scenario: Auth failure raises GazelleAuthError
- **WHEN** a request returns 401 or 403 and re-authentication fails
- **THEN** `GazelleAuthError` is raised

#### Scenario: Rate limit exhausted raises GazelleRateLimitError
- **WHEN** a 429 response is received and all retries are exhausted
- **THEN** `GazelleRateLimitError` is raised

#### Scenario: Not found raises GazelleNotFoundError
- **WHEN** a request returns 404
- **THEN** `GazelleNotFoundError` is raised

#### Scenario: Other non-2xx raises GazelleAPIError
- **WHEN** a request returns any other non-2xx status
- **THEN** `GazelleAPIError` is raised
