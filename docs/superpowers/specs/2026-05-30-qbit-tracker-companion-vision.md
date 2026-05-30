# qBittorrent Tracker Companion — Product Vision

- **Date:** 2026-05-30
- **Status:** Vision approved (Workflow 1). Not yet scaffolded.
- **Type:** New product — separate repo, depends on `python-gazelle`.

> This is the founding vision for a new product brainstormed inside the
> `python-gazelle` repo. When the dedicated repo is scaffolded, this document
> becomes that repo's founding vision doc.

## Vision

A self-hosted companion web app for managing private-tracker torrents through
qBittorrent. It runs alongside qBittorrent and presents, per tracker *type*, a
**cross-tracker release matrix**: rows are releases the user owns, columns are
trackers, and color-coded cells show each release's state on each tracker.

The first panel is **Music** (Orpheus, Redacted — the trackers `python-gazelle`
supports).

### The matrix (Music panel)

- **Row** = a logical release (an album), identified by file content.
- **Column** = a tracker.
- **Cell states** (color-coded):
  - **seeded** — listed on that tracker and seeding in qBittorrent (files on disk).
  - **exists, not seeded** — listed on the tracker but the user's copy isn't
    registered there → *cross-seed* candidate (only meaningful when the row's
    files are on disk, i.e. some cell in the row is seeded).
  - **absent** — not on that tracker → *upload* candidate.
  - **trumped** — distinct color; no actions allowed.

Action buttons (cross-seed, upload) are part of the long-term vision but are
sequenced after the read-only matrix (see Feature Map).

## Core data model

- **Rows = releases the user has in qBittorrent**, grouped by content. You cannot
  "upload" something you do not own, and "on disk" means qBittorrent is seeding
  it somewhere. Two qBit torrents of the same content on different trackers
  collapse into one row with two seeded cells.
- For each row, each non-seeded tracker column is resolved by searching that
  tracker for the release: found → cross-seed cell, not found → upload cell,
  trumped → trumped cell.

## The foundation: content/file matching

Everything rests on deciding **"is this the same release?"** — used both to group
the user's qBit torrents into rows and to detect a release's presence on another
tracker. The decision is made by **file content** (file names + sizes, total
size) — the same signal that determines whether a cross-seed is valid. Tracker
metadata (artist/album/year/format) is used only to *narrow* the tracker search;
the file match is the source of truth. This keeps the matrix honest (a wrong
match would produce a bad "absent → upload" or a bad "exists → cross-seed").

## Cross-cutting constraint: ban-safety

Building the matrix naively would require many tracker searches (each row × each
non-seeded tracker). **The app must never build the matrix by live-querying
trackers on page load.** Instead:

- All tracker I/O is funneled through one rate-limited layer that writes results
  into a local cache.
- `GET /matrix` reads the cache only — zero tracker calls.
- Refresh is a separate, user-triggered or scheduled, rate-limited background job.

qBittorrent carries no such risk (local API) and may be queried freely.

## Architecture (MVP)

New repo `qbit-tracker-companion`:

```
backend/   FastAPI — JSON API
  ├─ pygazelle (uv path dependency) ──► Orpheus / Redacted
  ├─ qbittorrent-api               ──► local qBittorrent WebUI API
  ├─ matching engine (pure, no network)
  ├─ matrix assembler
  └─ SQLite cache + config
frontend/  React + TypeScript + Vite + TanStack Table (SPA) ──► backend JSON
```

- **Backend:** FastAPI (async, pydantic-native — matches `python-gazelle`).
- **Frontend:** React + TS + Vite SPA; **TanStack Table** for the matrix grid.
- **Dependency on `python-gazelle`:** uv path dependency (editable) during
  co-development; switchable to a pinned git dependency later. No PyPI needed.
- **Deployment:** the read-only MVP needs **no direct disk mount** —
  qBittorrent's API reports file names, sizes, paths, and completion, which is
  all matching needs. The app needs only network access to qBittorrent's API and
  the trackers. "Same container" is a deployment preference, not a requirement;
  direct disk access becomes relevant only for V1 uploads.

### Components

- **qBit client wrapper** — thin layer over `qbittorrent-api`.
- **matching** — pure `same_release(files_a, files_b) -> confidence`.
- **trackers** — pygazelle search + file-list fetch + trumped state; the only
  rate-limited, cache-writing tracker I/O.
- **assembler** — combines qBit library + cached tracker data via matching into
  the matrix model.
- **api** — `GET /matrix` (cache), `POST /refresh` (rate-limited job),
  `GET/PUT /config`.
- **frontend** — renders the matrix grid; tracks refresh status.

## Testing strategy

Resolves the concern that `python-gazelle` is not fully integration-tested:

- **qBittorrent integration** — real qBittorrent in Docker; integration-test
  freely (local, no ban risk).
- **Trackers** — fixture-driven like `python-gazelle`; the only live calls are
  one-time, careful endpoint validations (`max_retries=0`) when first wiring each
  endpoint the app uses. Harden only the slice the app depends on.
- **Matching** — pure unit tests (the bulk of confidence).
- **Assembler** — unit tests with fake qBit + fake tracker data.
- **Frontend** — component tests against a mocked API.

Nothing in normal development or CI hammers a tracker.

## Feature map

### MVP — read-only matrix

Goal: full situational awareness, zero ban risk. Action buttons rendered but
disabled.

- **F1 · qBittorrent integration** — enumerate torrents, files+sizes, paths,
  tracker, seed state.
- **F2 · Content-matching engine** — pure file-content matching with confidence
  rules and edge cases (multi-disc, log/cue, scene).
- **F3 · Tracker query layer** — pygazelle search + file lists + trumped state;
  rate-limited; writes to cache. Harden the endpoints used; capture fixtures.
- **F4 · Matrix assembler** — rows × columns × cell-state from qBit + cache.
- **F5 · Persistence + config** — SQLite cache / matrix snapshots / match
  results; config for qBit creds + tracker API keys.
- **F6 · Web backend** — FastAPI JSON API (`/matrix`, `/refresh`, `/config`).
- **F7 · Web UI: Music panel** — React/TanStack matrix grid, color-coded cells,
  buttons disabled.
- **F8 · Deployment** — run alongside qBittorrent.

### Beta — cross-seed action

- **F9 · Cross-seed flow** — for an *exists-not-seeded* cell: fetch the .torrent,
  add to qBit against existing files, verify, seed. Leans on F2 for file
  compatibility. Moderate risk (writes to qBit only).

### V1 — upload action

- **F10 · Upload flow** — for an *absent* cell: build metadata, create the
  .torrent, upload via tracker API, add to qBit, seed. Highest risk (new tracker
  listings via API; per-tracker rules, dupe checks).

### Future

- **F11 · Additional panels** per tracker type (non-music), generalizing the
  matrix.
- The parked `python-gazelle` **upload/snatch monitoring** spec can feed the
  `trumped` cell-state and add proactive alerts.

### Dependency sketch

- MVP requires F1–F8; **F4 depends on F1, F2, F3, F5**.
- Beta (F9) depends on the MVP + F2.
- V1 (F10) depends on the MVP.

## Open items deferred to scaffolding / first plan

- Exact pagination + file-list shape of the gazelle search/torrent endpoints per
  tracker (capture fixtures when wiring F3).
- qBittorrent category/tag conventions used to identify a torrent's tracker.
- Confidence thresholds and edge-case rules for F2 (multi-CD, mixed formats,
  partial/incomplete torrents).
- Refresh cadence / scheduling defaults.
