## Context

`python-gazelle` is a new Python library (Python 3.11+) with no existing implementation — just a project scaffold. The Core API Client is the foundational layer; all other features (upload monitoring, cross-seed, cross-upload) depend on it. Two primary targets: Orpheus and Redacted, both Gazelle-based but with per-tracker API quirks.

## Goals / Non-Goals

**Goals:**
- Async-native HTTP client wrapping the full Gazelle API surface
- Resource-based API (`client.torrents.get(id)`) backed by Pydantic v2 models
- Transport layer that handles auth (cookie + API key), rate limiting, and retry independently of domain logic
- Tracker subclasses (`OrpheusClient`, `RedactedClient`) for per-tracker differences
- Sync wrapper with identical API surface, no duplicated method signatures

**Non-Goals:**
- CLI or daemon interface — library only
- Automation features (monitoring, cross-seed, cross-upload) — separate epics
- Support for Gazelle trackers beyond Orpheus and Redacted in this phase

## Decisions

### Async-native with sync wrapper (not dual implementation)
The async client is the source of truth. The sync wrapper drives it via `asyncio.run_coroutine_threadsafe()` against a persistent background event loop thread — not `asyncio.run()` per call. This preserves httpx connection pooling and works inside already-running loops (e.g., Jupyter).

**Alternative considered:** Two independent implementations (sync `requests` + async `httpx`). Rejected: doubles maintenance burden and surface area for bugs.

### Layered architecture: Transport + Domain
`GazelleTransport` owns httpx, auth, rate limiting, and retry. Resource objects call through the transport and know nothing about HTTP. This separation means transport logic (complex: token bucket, backoff, re-auth) is testable without instantiating a full client.

**Alternative considered:** Flat client where resources call httpx directly. Rejected: rate limiting and retry become tangled with business logic and are harder to test.

### Tracker subclasses over config objects
`OrpheusClient(GazelleClient)` and `RedactedClient(GazelleClient)` subclass the base client. Tracker-specific endpoints or field mappings are overrides on the subclass.

**Alternative considered:** Single client with `TrackerConfig` injection. Rejected: config objects push tracker differences into runtime data rather than type-checked code; subclasses are more discoverable and IDEs surface tracker-specific methods naturally.

### Pydantic v2 for response models
Automatic validation, coercion, and serialization with full type annotations. Models shared across trackers where schemas align; tracker-specific submodels where they diverge.

**Alternative considered:** stdlib dataclasses. Rejected: no built-in validation or coercion; nested model deserialization requires significant manual code.

## Risks / Trade-offs

- **Gazelle API is undocumented** → Mitigation: capture real API response fixtures from both trackers early; use these as model test inputs to catch schema drift.
- **Per-tracker quirks unknown until tested** → Mitigation: integration tests against both trackers before any automation feature starts; adapter overrides are easy to add in subclasses.
- **Sync wrapper adds threading complexity** → Mitigation: the pattern is well-established (mirrors httpx's own sync implementation); background thread is a daemon thread so it never blocks process exit.
- **Token-bucket rate limit values are approximate** → Mitigation: default conservatively (~3 req/s); make configurable at client instantiation.

## Open Questions

- Do Orpheus and Redacted support API key auth identically, or does one require session cookies only? → Confirm during integration testing; fall back to cookie-only for that tracker if needed.
