# Upload & Snatch Monitoring — Design

- **Date:** 2026-05-30
- **Epic:** python-gazelle-p53 ([Epic] Upload Monitoring — to be renamed/expanded to cover snatches)
- **Status:** Design approved, pending spec review

> **Correction (2026-06-04):** Work that landed after this doc was written has
> overtaken three points below. The OpenSpec delta is the source of truth where
> they differ:
> 1. **`UserTorrent` has no `group_name`.** The shipped model exposes `name`
>    (release name), `group_id`, `torrent_id`, `torrent_size`, `artist_id`,
>    `artist_name`. Read `group_name` as `name` throughout this doc.
> 2. **The endpoint takes an explicit `user_id`.** The shipped signature is
>    `UserResource.torrents(user_id, type, limit, offset)`, not `torrents(type)`.
>    The monitor resolves the id via `me().id` and passes it in.
> 3. **The `user_torrents` endpoint already shipped** (commit `0f39d3b`), with
>    unit + model tests. It is no longer new work — the "Beads impact" section's
>    new-endpoint sub-feature is moot; only the monitor + sync wrapper remain.

## Summary

Watch the current user's **uploaded** and **snatched** torrents for **deletion**
and **trump**, and surface those as typed change events. The library
auto-discovers the watch list from the tracker and exposes a stateless
`poll()` primitive: each call returns the changes since the previous snapshot.
The caller owns cadence and any cross-restart persistence.

This expands the original epic (uploads only) to also cover torrents the user
has snatched — the same event model over a second source list, so a user can
react when a torrent they are seeding is deleted or trumped (stop seeding, grab
the replacement).

## Goals

- Detect deletion and trump of the user's uploaded and snatched torrents.
- Auto-discover the watch list (no manual ID bookkeeping by the caller).
- A stateless, easily testable `poll()` API — no library-owned loop, no callbacks.
- Stay safely within tracker rate limits (no per-torrent polling of the whole list).
- Work on both Orpheus and Redacted, honoring their schema divergences.

## Non-goals

- No library-run background loop, scheduler, or callback registration. The
  caller drives `poll()` on whatever cadence they choose.
- No torrent-client integration (removing/adding torrents downstream is the
  caller's job, reacting to emitted events).
- No tracking of snatch-count popularity on the user's uploads (a different
  feature that was explicitly de-scoped during brainstorming).
- No automatic disk persistence; the library offers serialization, the caller
  decides where/whether to store it.

## Architecture

Three isolated, independently testable units:

```
client.user.torrents(type=…)      new endpoint — dumb typed data
        │
        ▼
TorrentMonitor.poll()             logic — snapshot + diff + classify
   ├─ holds last snapshot (in memory)
   ├─ dump_state() / load_state()
   └─ returns list[TorrentChangeEvent]
        │
        ▼
models: UserTorrent,              typed shapes (GazelleModel)
        TorrentChangeEvent
```

- **`UserResource.torrents(type, limit, offset)`** → `list[UserTorrent]`,
  wrapping the Gazelle `user_torrents` action. Reusable on its own; fills a real
  gap in endpoint coverage. Lives in the existing `resources/user.py`.
- **`TorrentMonitor`** (new `src/pygazelle/monitoring.py`) — owns the snapshot,
  performs diff + classification in `poll()`, returns events. Constructed via a
  `client.monitor(...)` factory. Resolves the current user id once via
  `user.me()` and caches it.
- **Models** in `src/pygazelle/models/` extending `GazelleModel`, following the
  per-tracker divergence conventions (Optional / union fields).
- **`TorrentMonitorSync`** in `sync.py` mirrors the async monitor for the
  synchronous API surface.

## Public API

```python
monitor = client.monitor(sources=("uploaded", "snatched"))  # default: both

events = await monitor.poll()        # first call establishes baseline → []
for ev in events:
    ev.kind                          # "deleted" | "trumped" | "removed"
    ev.source                        # "uploaded" | "snatched"
    ev.torrent_id
    ev.group_id
    ev.group_name
    ev.replacement_torrent_id        # set only when kind == "trumped", else None

# Cross-restart persistence (caller-owned storage)
state = monitor.dump_state()         # json-serializable dict
monitor.load_state(state)            # restore prior snapshot
```

### Models

```python
class UserTorrent(GazelleModel):
    torrent_id: int
    group_id: int
    group_name: str
    # Additional fields (size, snatched, seeding flag, …) added as the captured
    # fixtures reveal them; divergent fields made Optional per convention.

class TorrentChangeEvent(GazelleModel):
    kind: Literal["deleted", "trumped", "removed"]
    source: Literal["uploaded", "snatched"]
    torrent_id: int
    group_id: int
    group_name: str
    replacement_torrent_id: int | None = None
```

## Detection mechanism — snapshot diff

Polling each watched torrent individually would risk rate-limit bans and scale
badly with large snatch lists. Instead, `poll()` diffs successive snapshots of
the `user_torrents` lists:

1. Ensure `user_id` — fetch `me()` once, cache it.
2. For each selected source, fetch the **full** list (paginate to exhaustion)
   and build the current snapshot: `{source: {torrent_id: (group_id, group_name)}}`.
3. If there is no prior snapshot → store this as the baseline and return `[]`.
4. Diff per source: torrent IDs present in the prior snapshot but absent now are
   **removal candidates**.
5. Classify each removal with **one targeted lookup** (only for removed torrents,
   never the whole list):
   - replacement torrent present in the same group → `trumped`
     (`replacement_torrent_id` = the replacement);
   - group gone, or `torrent` lookup returns `GazelleNotFoundError`, with no
     replacement → `deleted`;
   - cannot determine → `removed` (unknown removal).
6. Commit the new snapshot **only after** the full fetch + classification
   succeeds, then return the events. A mid-poll failure leaves the prior
   snapshot intact.

### Cost per poll

≈ (pages of uploaded list + pages of snatched list) + (one lookup per *removed*
torrent). Removals are normally few, so request volume stays well clear of
ban territory. All requests pass through the existing `TokenBucket` rate
limiter and retry/backoff layer.

## Error handling

- `GazelleNotFoundError` during classification is a *signal* (confirmed
  deletion), not a propagated error.
- Transient/server errors during list fetch propagate to the caller after the
  transport's normal retries; the in-memory snapshot is unchanged (atomic
  commit in step 6).
- No retry loops on auth errors (ban risk) — auth failures propagate.

## Testing

- **Unit** (mock transport): baseline-empty first poll, deletion detected,
  trump detected with replacement, ambiguous → `removed`, no-change poll returns
  `[]`, pagination across multiple pages, `dump_state`/`load_state` round-trip,
  source filtering (uploaded-only / snatched-only / both), atomic-on-error
  (snapshot unchanged when a mid-poll fetch raises).
- **Model** (fixture-driven): `UserTorrent` parses Orpheus and Redacted
  `user_torrents` fixtures. Requires capturing those fixtures (see Risks).
- **Integration** (live, opt-in): a single read-only `user_torrents` call with
  `max_retries=0`, per the project's live-API care rules.

## Risks & assumptions to verify

- **A — `user_torrents` action shape.** It is a standard Gazelle action
  (`type` ∈ uploaded, snatched, seeding, leeching, …), but our fixtures do not
  cover it and the action name / params / response shape may diverge between
  Orpheus and Redacted. Implementation captures fixtures first (extend
  `devtools/capture_fixtures.py`) and adapts the model per the divergence
  convention.
- **B — liveness via the list.** Diff detection assumes deleted/trumped torrents
  *drop off* the `user_torrents` list. **Decision: verify this first.** The
  implementation plan leads with a small spike — capture a `user_torrents`
  fixture and confirm whether deleted torrents disappear. If they drop off, ship
  pure snapshot-diff. If they linger, add a targeted per-removal `torrent`
  recheck to confirm deletion. Do not build the fallback before the data
  justifies it.

## Beads impact (for the planning phase, not yet created)

- **New** sub-feature: the `user_torrents` endpoint (not covered by `6nh`/`1fm`).
- `python-gazelle-6nh` (polling) → the snapshot-diff + classification engine.
- `python-gazelle-1fm` ("callback/event model") → **rescoped** to the stateless
  event model + `poll()` API (callbacks dropped). Update the issue.
- `python-gazelle-p53` epic description → expanded to include **snatched**
  sources, not only uploads.
