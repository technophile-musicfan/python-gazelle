# Capability: gazelle-transport

## Purpose

The transport layer handles all HTTP communication with Gazelle-based tracker APIs. It is responsible for authentication (cookie-based and API key), rate limiting via a token-bucket algorithm, retry logic with exponential backoff for transient errors on reads, a POST-based write path for mutating actions (with authkey injection and deliberately no retry on non-idempotent writes), and surfacing a typed exception hierarchy so callers can handle error conditions precisely.

## Requirements
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

### Requirement: Write request path
The transport SHALL provide a POST-based write method for mutating actions, supporting form and multipart bodies and injecting the per-user `auth` token (authkey) that write actions require.

#### Scenario: Write POSTs to ajax.php
- **WHEN** a mutating action is invoked via the write method
- **THEN** the request is sent as a POST to `ajax.php` with the action as a query param and the parameters in a form/multipart body

#### Scenario: Auth token injected and cached
- **WHEN** a write is sent and the caller did not supply an `auth` value
- **THEN** the transport fetches the user's authkey (from the index response), caches it, and includes it in the request body

#### Scenario: Caller-supplied auth is preserved
- **WHEN** a write supplies its own `auth` value
- **THEN** the transport does not fetch or override it

#### Scenario: Multipart file upload supported
- **WHEN** a write supplies file parts (e.g. a rip log)
- **THEN** the request is sent as `multipart/form-data`

#### Scenario: Extra query params supported
- **WHEN** an action reads a parameter from the query string (e.g. add_log's `id`)
- **THEN** the write method places that parameter in the query string alongside the action

### Requirement: Non-idempotent write safety
The transport SHALL NOT retry non-idempotent writes on transient errors, to avoid double-applying a write that may already have taken effect server-side.

#### Scenario: No retry on 429 or 5xx for writes
- **WHEN** a write receives a 429 or 5xx response
- **THEN** the transport raises the corresponding error immediately, without retrying

#### Scenario: Single re-auth on an expired cookie session
- **WHEN** a cookie-mode write receives a 401 (session expired, request rejected before processing)
- **THEN** the transport re-authenticates and resends the write exactly once

#### Scenario: No resend on 403
- **WHEN** a write receives a 403
- **THEN** the transport does not re-authenticate or resend it, since a 403 is "forbidden" rather than an expired session

