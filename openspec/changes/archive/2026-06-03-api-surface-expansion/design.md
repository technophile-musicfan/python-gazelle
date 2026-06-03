## Context

A documentation-only reconciliation. The implementation already exists and is
covered by tests; this change exists solely to bring the OpenSpec main specs
back in line with shipped behavior after a series of lightweight, non-spec'd
endpoint additions.

## Decisions

- **Capability altitude, not per-field.** Specs describe capabilities (resource
  namespaces, the write path, the divergence-handling approach), not every field.
  Field-level enrichment (extra model fields added to existing models) is not
  separately spec'd; only capability-level changes are. This keeps the specs
  stable under the lightweight endpoint workflow instead of rotting on every
  added field.
- **Tolerant base models supersede subclasses.** The `response-models`
  "Tracker-specific model variants" requirement (per-tracker subclasses) is
  removed and replaced with tolerant base models (Optional + union types),
  matching the actual implementation.
- **Write safety.** Non-idempotent writes are never retried on transient errors
  (429/5xx raise immediately); the only resend is a single re-auth on a
  cookie-mode 401 (request rejected before processing). A 403 is not resent.

## Risks

- No functional risk (no code change). The standing risk is spec/code drift
  recurring; mitigated by the capability-altitude convention above.
