## ADDED Requirements

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
