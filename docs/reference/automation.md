# Automation

Higher-level helpers built on the client: monitoring the current user's torrents,
cross-seeding a release to another tracker, and cross-uploading one. These are
exported from the top-level `pygazelle` package.

## Monitoring

Watch the current user's uploaded and snatched torrents for deletion or trump.
Construct a monitor with `client.monitor(...)`.

::: pygazelle.TorrentMonitor

::: pygazelle.TorrentChangeEvent

## Cross-seed

Find the same release on a target tracker (metadata match + strict file-list
verification) and fetch its `.torrent`.

::: pygazelle.cross_seed

::: pygazelle.cross_seed_sync

::: pygazelle.find_candidates

::: pygazelle.verify_match

::: pygazelle.CrossSeedResult

## Cross-upload

Two-phase upload of a release to another tracker: a read-only `prepare_upload`
(map metadata, detect duplicates, build a draft) followed by an explicit,
duplicate-gated `submit_upload`. The caller builds the target `.torrent`; the
library exposes the target announce URL via `client.user.announce_url()`.

::: pygazelle.prepare_upload

::: pygazelle.submit_upload

::: pygazelle.prepare_upload_sync

::: pygazelle.submit_upload_sync

::: pygazelle.map_metadata

::: pygazelle.duplicate_check

::: pygazelle.UploadDraft

::: pygazelle.UploadResult

::: pygazelle.DuplicateMatch
