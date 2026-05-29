# python-gazelle — Feature Map

**Date:** 2026-05-30

## Dependency Map

```
Core API Client
    └── Upload Monitoring
    └── Cross-Seed
            └── Cross-Upload
```

---

## MVP — Core API Client

**Goal:** A stable, well-tested foundation that all automation features build on.

- Authentication (cookie/session-based, API key where supported)
- Rate limiting and retry logic
- Full Gazelle endpoint coverage: torrents, artists, requests, collages, user, inbox, notifications
- Tracker-specific adapters for Orpheus and Redacted (API quirks, endpoint signature differences)
- Typed response models (dataclasses or Pydantic)
- Test suite validating both trackers

---

## Beta — Automation Layer

**Goal:** Core automation utilities for upload monitoring and cross-seeding.

### Upload Monitoring
- Poll notifications/torrent endpoints to detect when user uploads are deleted or trumped
- Callback/event model so scripts can react (e.g., remove torrent from client)

### Cross-Seed
- **API match:** Query target tracker by metadata (artist, album, format, year) to find candidate releases
- **File match:** Compare file lists between candidate and local files to verify exact match before seeding
- Produce a `.torrent` ready to add to a torrent client

---

## V1 — Cross-Upload

**Goal:** Upload a release from one tracker to the other with correct metadata.

- Fetch source `.torrent` + metadata from origin tracker
- Map metadata between tracker schemas (artist, album, year, tags, format, media, description)
- Submit upload to target tracker via API
- Duplicate detection: check target tracker before uploading to avoid conflicts
