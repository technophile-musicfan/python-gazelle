## Why

The OpenSpec main specs were last updated at the `2026-05-30-core-api-client`
baseline. Since then a large amount of read- and write-endpoint coverage shipped
via the project's lightweight endpoint-addition workflow, which intentionally
skips per-endpoint delta specs. As a result the main specs (`gazelle-client`,
`gazelle-transport`, `response-models`) drifted behind the implemented surface.

This change is a **catch-up**: it records the now-shipped capabilities as deltas
and folds them into the main specs so the specs match reality. There are no code
changes — every behavior documented here is already implemented and tested.

## What Changes

- **gazelle-client**: document the new resource namespaces (`bookmarks`,
  `subscriptions`, `site`); the expanded methods on existing resources
  (`torrents.get_group`/`add_tag`/`add_log`, `artists.similar`,
  `user.get`/`search`/`torrents`); and the `requests` resource
  (`get`/`search`/`fill`).
- **gazelle-transport**: document the write request path (POST + form/multipart
  body + authkey injection) and the non-idempotent write-safety rules (no retry
  on 429/5xx; single re-auth on a cookie-mode 401; no resend on 403).
- **response-models**: correct the tracker-divergence requirement — the
  implemented approach uses tolerant **base** models (Optional fields + union
  types), **not** per-tracker subclasses — and record endpoint model coverage.

## Non-goals

- **Forum** endpoints — intentionally out of scope (closed won't-do).
- **upload** — owned by the cross-upload epic, not these resources.
- **Pagination metadata** exposure on list endpoints — tracked separately.
