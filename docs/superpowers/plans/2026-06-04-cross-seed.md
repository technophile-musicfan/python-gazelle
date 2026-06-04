# Cross-Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Given a source torrent id on one Gazelle tracker and a target client, find the same release on the target tracker via metadata search + strict file-list verification, and return the target's `.torrent` bytes.

**Architecture:** A new module `src/pygazelle/crossseed.py` with three functions — `find_candidates` (metadata search + cheap pre-filter), `verify_match` (strict file-list comparison), and `cross_seed` (end-to-end orchestrator) — plus a `CrossSeedResult` frozen dataclass. All API-only, built on existing `torrents.get` / `torrents.search` / `torrents.download` and the already-parsed `Torrent.files`/`file_path`/`group`. A sync wrapper lives in `sync.py`.

**Tech Stack:** Python 3.11+, httpx (async), pydantic v2, pytest (`asyncio_mode = "auto"`), uv, ruff, basedpyright.

---

## Background the implementer needs

- **Existing APIs (do not reimplement):**
  - `await client.torrents.get(id) -> Torrent`. Raises `GazelleNotFoundError` (from `pygazelle.errors`) on HTTP 404.
  - `await client.torrents.search(query: str, **params) -> list[TorrentResult]` — wraps the `browse` action (`searchstr=query` plus any params like `artistname=`, `groupname=`).
  - `await client.torrents.download(id) -> bytes`.
- **`Torrent`** (`src/pygazelle/models/torrents.py`): `id`, `media`, `format`, `encoding`, `size`, `file_count`, `file_path` (top-level folder), `file_list` (raw), `files` (property → `list[TorrentFile]` where `TorrentFile` has `.path` + `.size`), and `group: TorrentGroup | None`.
- **`TorrentGroup`**: `id`, `name` (the album), `year`, `artists: list[TorrentArtist]` (each `TorrentArtist` has `.id`, `.name`). The model lifts `musicInfo.artists` into `artists` automatically.
- **`TorrentResult`** (a search/browse group row): `group_id`, `group_name`, `artist`, `group_year`, `max_size`, `torrents: list[BrowseTorrent]`. **`BrowseTorrent`**: `torrent_id`, `size`, `file_count`, `format`, `encoding`, `media`.
- **Sync** (`src/pygazelle/sync.py`): `GazelleSyncClient` holds `._async` (the async `GazelleClient`) and `._bg` (a `_BackgroundLoop` with `.run(coro) -> result`).
- **No import cycle:** `crossseed.py` imports `GazelleClient` only under `TYPE_CHECKING`, and nothing imports `crossseed` except `sync.py` and `__init__.py` (one-directional). Do not add a `client.py` → `crossseed` import.
- **Conventions:** every module starts with `from __future__ import annotations`; ruff line-length 100; basedpyright strict-clean for `src/` (run the WHOLE project: `uv run basedpyright`, not just one file — test-file issues count); codespell-clean; tests are `async def test_*` (`asyncio_mode = "auto"`, no decorator). Run tests with `uv run pytest ...`. A uv warning `VIRTUAL_ENV ... does not match` is harmless — ignore it.
- **Cross-package test import:** `tests/support.py` is already importable as `tests.support` (the repo has `tests/__init__.py` and `pythonpath = ["."]` / basedpyright `extraPaths = ["."]`). Add new helpers there.

## File Structure

- **Create** `src/pygazelle/crossseed.py` — `CrossSeedResult`, `verify_match`, `find_candidates`, `cross_seed`.
- **Modify** `src/pygazelle/sync.py` — add `cross_seed_sync(...)`.
- **Modify** `src/pygazelle/__init__.py` — export `cross_seed`, `find_candidates`, `verify_match`, `CrossSeedResult`, `cross_seed_sync`.
- **Modify** `tests/support.py` — add `CrossSeedTransport` + `make_torrent_payload` + `make_browse_group` + `make_browse_row`.
- **Create** `tests/test_crossseed.py` — unit tests for verify/find/orchestrator.
- **Create** `tests/test_crossseed_sync.py` — sync surface test.
- **Create** `tests/integration/test_crossseed_live.py` — opt-in cross-tracker read.
- **Modify** `README.md` — cross-seed usage example.

---

## Task 1: `CrossSeedResult` + module skeleton

**Files:**
- Create: `src/pygazelle/crossseed.py`
- Test: `tests/test_crossseed.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_crossseed.py`:

```python
from pygazelle.crossseed import CrossSeedResult


def test_cross_seed_result_holds_fields():
    r = CrossSeedResult(
        match=None,  # type: ignore[arg-type]  # placeholder; real match is a Torrent
        torrent_file=b"data",
        source_torrent_id=1,
        target_torrent_id=2,
    )
    assert r.torrent_file == b"data"
    assert r.source_torrent_id == 1
    assert r.target_torrent_id == 2
    assert r.confidence == "exact"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_crossseed.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pygazelle.crossseed'`.

- [ ] **Step 3: Create the module + dataclass**

Create `src/pygazelle/crossseed.py`:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .errors import GazelleNotFoundError
from .models.torrents import Torrent

if TYPE_CHECKING:
    from .client import GazelleClient

logger = logging.getLogger("pygazelle.crossseed")


@dataclass(frozen=True)
class CrossSeedResult:
    """A confirmed cross-seed match plus the target tracker's .torrent bytes."""

    match: Torrent
    torrent_file: bytes
    source_torrent_id: int
    target_torrent_id: int
    confidence: Literal["exact"] = "exact"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_crossseed.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/crossseed.py tests/test_crossseed.py
git commit -F - <<'EOF'
feat(crossseed): add CrossSeedResult and module skeleton

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 2: Test fakes for cross-seed

**Files:**
- Modify: `tests/support.py`

- [ ] **Step 1: Append the cross-seed fakes to `tests/support.py`**

Add to the END of `tests/support.py` (it already imports `Any` and defines monitoring fakes):

```python
def make_torrent_payload(
    *,
    torrent_id: int,
    group_id: int,
    group_name: str,
    year: int,
    artist: str,
    file_path: str,
    files: list[tuple[str, int]],
    fmt: str = "FLAC",
    encoding: str = "Lossless",
    media: str = "CD",
) -> dict[str, Any]:
    """Build an action=torrent response ({"torrent": ..., "group": ...}) that
    validates as a Torrent with a file list and group metadata.

    ``files`` is a list of (relative path, size) pairs.
    """
    file_list = "|||".join(f"{path}{{{{{{{size}}}}}}}" for path, size in files)
    total = sum(size for _, size in files)
    return {
        "torrent": {
            "id": torrent_id,
            "media": media,
            "format": fmt,
            "encoding": encoding,
            "scene": False,
            "hasLog": False,
            "hasCue": False,
            "logScore": 0,
            "fileCount": len(files),
            "size": total,
            "seeders": 1,
            "leechers": 0,
            "snatched": 0,
            "time": "2020-01-01 00:00:00",
            "filePath": file_path,
            "userId": 1,
            "username": "uploader",
            "fileList": file_list,
        },
        "group": {
            "id": group_id,
            "name": group_name,
            "year": year,
            "musicInfo": {"artists": [{"id": 1, "name": artist}]},
        },
    }


def make_browse_row(
    *,
    torrent_id: int,
    size: int,
    file_count: int,
    fmt: str = "FLAC",
    encoding: str = "Lossless",
    media: str = "CD",
) -> dict[str, Any]:
    """A BrowseTorrent row inside a browse group result."""
    return {
        "torrentId": torrent_id,
        "size": size,
        "fileCount": file_count,
        "format": fmt,
        "encoding": encoding,
        "media": media,
    }


def make_browse_group(
    *,
    group_id: int,
    group_name: str,
    artist: str,
    year: int,
    torrents: list[dict[str, Any]],
) -> dict[str, Any]:
    """A browse result group (action=browse 'results' entry)."""
    return {
        "groupId": group_id,
        "groupName": group_name,
        "artist": artist,
        "groupYear": year,
        "maxSize": max((t["size"] for t in torrents), default=0),
        "totalSeeders": 1,
        "totalLeechers": 0,
        "totalSnatched": 0,
        "torrents": torrents,
    }


class CrossSeedTransport:
    """Fake transport for one side (source or target) of a cross-seed test.

    torrents: {id: action=torrent response} (use make_torrent_payload).
    browse_results: list of browse group dicts (use make_browse_group); returned
        for any 'browse' action regardless of params.
    download_bytes: bytes returned by download().
    """

    def __init__(
        self,
        *,
        torrents: dict[int, dict[str, Any]] | None = None,
        browse_results: list[dict[str, Any]] | None = None,
        download_bytes: bytes = b"torrent-file-bytes",
    ) -> None:
        self._torrents = torrents or {}
        self._browse_results = browse_results or []
        self._download_bytes = download_bytes
        self.downloaded: list[int] = []
        self.torrent_gets: list[int] = []

    async def request(self, action: str, **params: Any) -> Any:
        if action == "torrent":
            tid = params["id"]
            self.torrent_gets.append(tid)
            from pygazelle.errors import GazelleNotFoundError

            if tid not in self._torrents:
                raise GazelleNotFoundError(f"torrent {tid} not found")
            return self._torrents[tid]
        if action == "browse":
            return {"results": self._browse_results}
        raise AssertionError(f"unexpected action: {action}")

    async def download(self, torrent_id: int) -> bytes:
        self.downloaded.append(torrent_id)
        return self._download_bytes
```

- [ ] **Step 2: Sanity-check the import**

Run: `uv run python -c "from tests.support import CrossSeedTransport, make_torrent_payload, make_browse_group, make_browse_row; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Verify the payload round-trips through the real model**

Run this one-off check (confirms the fileList string and group metadata parse):

```bash
uv run python -c "
from pygazelle.models.torrents import Torrent
from tests.support import make_torrent_payload
p = make_torrent_payload(torrent_id=1, group_id=5, group_name='Album', year=2020, artist='Band', file_path='Album [FLAC]', files=[('01.flac', 30), ('02.flac', 28)])
t = Torrent.model_validate({**p['torrent'], 'group': p['group']})
assert t.file_path == 'Album [FLAC]'
assert sorted((f.path, f.size) for f in t.files) == [('01.flac', 30), ('02.flac', 28)]
assert t.group.name == 'Album' and t.group.artists[0].name == 'Band'
assert t.format == 'FLAC' and t.size == 58 and t.file_count == 2
print('payload OK')
"
```
Expected: prints `payload OK`. If the file list does not parse, fix the `file_list` join in `make_torrent_payload` (the raw format is `name{{{size}}}|||name{{{size}}}`).

- [ ] **Step 4: Commit**

```bash
git add tests/support.py
git commit -F - <<'EOF'
test(crossseed): add CrossSeedTransport fake + payload builders

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 3: `verify_match` (strict file-list verification — xx0)

**Files:**
- Modify: `src/pygazelle/crossseed.py`
- Test: `tests/test_crossseed.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_crossseed.py`:

```python
from pygazelle.crossseed import verify_match
from pygazelle.models.torrents import Torrent
from tests.support import make_torrent_payload


def _torrent(**kw) -> Torrent:
    p = make_torrent_payload(**kw)
    return Torrent.model_validate({**p["torrent"], "group": p["group"]})


_BASE = dict(group_id=5, group_name="Album", year=2020, artist="Band")


def test_verify_match_identical_passes_any_order():
    src = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE)
    cand = _torrent(torrent_id=2, file_path="Album [FLAC]", files=[("02.flac", 28), ("01.flac", 30)], **_BASE)
    assert verify_match(src, cand) is True


def test_verify_match_differing_top_folder_rejects():
    src = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    cand = _torrent(torrent_id=2, file_path="Band - Album (2020) [FLAC]", files=[("01.flac", 30)], **_BASE)
    assert verify_match(src, cand) is False


def test_verify_match_differing_size_rejects():
    src = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    cand = _torrent(torrent_id=2, file_path="Album [FLAC]", files=[("01.flac", 31)], **_BASE)
    assert verify_match(src, cand) is False


def test_verify_match_missing_file_rejects():
    src = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE)
    cand = _torrent(torrent_id=2, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    assert verify_match(src, cand) is False


def test_verify_match_empty_filelists_do_not_match():
    src = _torrent(torrent_id=1, file_path="X", files=[], **_BASE)
    cand = _torrent(torrent_id=2, file_path="X", files=[], **_BASE)
    assert verify_match(src, cand) is False
```

- [ ] **Step 2: Run → expect FAIL** (`cannot import name 'verify_match'`).

Run: `uv run pytest tests/test_crossseed.py -k verify -q`

- [ ] **Step 3: Implement `verify_match`**

Add to `src/pygazelle/crossseed.py` (after `CrossSeedResult`):

```python
def verify_match(source: Torrent, candidate: Torrent) -> bool:
    """Strict cross-seed match: identical top-level folder and identical sorted
    (path, size) file list. Empty file lists never match.
    """
    if source.file_path != candidate.file_path:
        return False
    source_files = sorted((f.path, f.size) for f in source.files)
    if not source_files:
        return False
    candidate_files = sorted((f.path, f.size) for f in candidate.files)
    return source_files == candidate_files
```

- [ ] **Step 4: Run → expect PASS** (5 passed).

Run: `uv run pytest tests/test_crossseed.py -k verify -q`

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/crossseed.py tests/test_crossseed.py
git commit -F - <<'EOF'
feat(crossseed): strict file-list verify_match (xx0)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 4: `find_candidates` (metadata search + cheap pre-filter — hs3)

**Files:**
- Modify: `src/pygazelle/crossseed.py`
- Test: `tests/test_crossseed.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_crossseed.py`:

```python
from pygazelle.client import GazelleClient
from pygazelle.crossseed import find_candidates
from tests.support import CrossSeedTransport, make_browse_group, make_browse_row


def _client(transport) -> GazelleClient:
    return GazelleClient(transport)  # pyright: ignore[reportArgumentType]


async def test_find_candidates_prefilters_wrong_format():
    source = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE)
    # source: FLAC/Lossless/CD, size 58, file_count 2
    target = CrossSeedTransport(
        browse_results=[
            make_browse_group(
                group_id=9, group_name="Album", artist="Band", year=2020,
                torrents=[
                    make_browse_row(torrent_id=20, size=58, file_count=2),  # matches
                    make_browse_row(torrent_id=21, size=58, file_count=2, fmt="MP3", encoding="320"),  # wrong format
                    make_browse_row(torrent_id=22, size=99, file_count=2),  # wrong size
                ],
            )
        ],
        torrents={
            20: make_torrent_payload(torrent_id=20, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE),
        },
    )
    candidates = await find_candidates(source, _client(target))
    # Only torrent 20 survives the cheap pre-filter, so only it is fetched.
    assert target.torrent_gets == [20]
    assert [c.id for c in candidates] == [20]


async def test_find_candidates_groupname_fallback_when_no_artist_hits():
    source = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    # First (artist-scoped) search returns nothing; fallback returns a candidate.
    # CrossSeedTransport returns the same browse_results regardless of params, so
    # to exercise the fallback we assert it still finds the candidate via groupname.
    target = CrossSeedTransport(
        browse_results=[
            make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020,
                              torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)])
        ],
        torrents={20: make_torrent_payload(torrent_id=20, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)},
    )
    candidates = await find_candidates(source, _client(target))
    assert [c.id for c in candidates] == [20]


async def test_find_candidates_caps_deep_checks():
    source = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    rows = [make_browse_row(torrent_id=100 + i, size=30, file_count=1) for i in range(10)]
    torrents = {100 + i: make_torrent_payload(torrent_id=100 + i, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE) for i in range(10)}
    target = CrossSeedTransport(
        browse_results=[make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020, torrents=rows)],
        torrents=torrents,
    )
    candidates = await find_candidates(source, _client(target), max_deep_checks=3)
    assert len(target.torrent_gets) == 3  # capped
    assert len(candidates) == 3
```

- [ ] **Step 2: Run → expect FAIL** (`cannot import name 'find_candidates'`).

Run: `uv run pytest tests/test_crossseed.py -k find_candidates -q`

- [ ] **Step 3: Implement `find_candidates`**

Add to `src/pygazelle/crossseed.py`:

```python
DEFAULT_MAX_DEEP_CHECKS = 5


async def find_candidates(
    source: Torrent,
    target_client: GazelleClient,
    *,
    max_deep_checks: int = DEFAULT_MAX_DEEP_CHECKS,
) -> list[Torrent]:
    """Search the target tracker by the source's artist/album, cheaply pre-filter
    candidates on format/encoding/media/size/file_count, then fetch the full
    file list for each survivor (bounded by ``max_deep_checks``).
    """
    artist = (
        source.group.artists[0].name
        if source.group and source.group.artists
        else None
    )
    album = source.group.name if source.group else None

    results = []
    if artist:
        params: dict[str, str | int] = {"artistname": artist}
        if album:
            params["groupname"] = album
        results = await target_client.torrents.search("", **params)
    if not results and album:
        results = await target_client.torrents.search("", groupname=album)

    candidate_ids: list[int] = []
    for group in results:
        for row in group.torrents:  # BrowseTorrent
            if (
                row.format == source.format
                and row.encoding == source.encoding
                and row.media == source.media
                and row.size == source.size
                and row.file_count == source.file_count
            ):
                candidate_ids.append(row.torrent_id)

    if len(candidate_ids) > max_deep_checks:
        logger.warning(
            "cross-seed: %d candidates exceed the deep-check cap (%d); "
            "checking only the first %d",
            len(candidate_ids),
            max_deep_checks,
            max_deep_checks,
        )
        candidate_ids = candidate_ids[:max_deep_checks]

    candidates: list[Torrent] = []
    for cid in candidate_ids:
        try:
            candidates.append(await target_client.torrents.get(cid))
        except GazelleNotFoundError:
            continue
    return candidates
```

- [ ] **Step 4: Run → expect PASS** (3 passed).

Run: `uv run pytest tests/test_crossseed.py -k find_candidates -q`

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/crossseed.py tests/test_crossseed.py
git commit -F - <<'EOF'
feat(crossseed): metadata candidate discovery with cheap pre-filter (hs3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 5: `cross_seed` orchestrator

**Files:**
- Modify: `src/pygazelle/crossseed.py`
- Test: `tests/test_crossseed.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_crossseed.py`:

```python
from pygazelle.crossseed import CrossSeedResult, cross_seed


async def test_cross_seed_happy_path_returns_torrent_bytes():
    files = [("01.flac", 30), ("02.flac", 28)]
    source_t = CrossSeedTransport(
        torrents={1: make_torrent_payload(torrent_id=1, file_path="Album [FLAC]", files=files, **_BASE)}
    )
    target_t = CrossSeedTransport(
        browse_results=[make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020,
                                          torrents=[make_browse_row(torrent_id=20, size=58, file_count=2)])],
        torrents={20: make_torrent_payload(torrent_id=20, file_path="Album [FLAC]", files=files, **_BASE)},
        download_bytes=b"the-torrent",
    )
    result = await cross_seed(_client(source_t), 1, _client(target_t))
    assert isinstance(result, CrossSeedResult)
    assert result.torrent_file == b"the-torrent"
    assert result.source_torrent_id == 1
    assert result.target_torrent_id == 20
    assert result.confidence == "exact"
    assert target_t.downloaded == [20]


async def test_cross_seed_no_filelist_match_returns_none():
    source_t = CrossSeedTransport(
        torrents={1: make_torrent_payload(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)}
    )
    target_t = CrossSeedTransport(
        browse_results=[make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020,
                                          torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)])],
        # candidate has same size/format but a different top folder -> verify rejects
        torrents={20: make_torrent_payload(torrent_id=20, file_path="DIFFERENT", files=[("01.flac", 30)], **_BASE)},
    )
    assert await cross_seed(_client(source_t), 1, _client(target_t)) is None
    assert target_t.downloaded == []  # nothing downloaded when no match


async def test_cross_seed_source_without_filelist_returns_none():
    source_t = CrossSeedTransport(
        torrents={1: make_torrent_payload(torrent_id=1, file_path="X", files=[], **_BASE)}
    )
    target_t = CrossSeedTransport()
    assert await cross_seed(_client(source_t), 1, _client(target_t)) is None


async def test_cross_seed_no_search_hits_returns_none():
    source_t = CrossSeedTransport(
        torrents={1: make_torrent_payload(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)}
    )
    target_t = CrossSeedTransport(browse_results=[])  # nothing on target
    assert await cross_seed(_client(source_t), 1, _client(target_t)) is None
```

- [ ] **Step 2: Run → expect FAIL** (`cannot import name 'cross_seed'`).

Run: `uv run pytest tests/test_crossseed.py -k cross_seed -q`

- [ ] **Step 3: Implement `cross_seed`**

Add to `src/pygazelle/crossseed.py`:

```python
async def cross_seed(
    source_client: GazelleClient,
    source_torrent_id: int,
    target_client: GazelleClient,
    *,
    max_deep_checks: int = DEFAULT_MAX_DEEP_CHECKS,
) -> CrossSeedResult | None:
    """Find ``source_torrent_id`` (on ``source_client``) on ``target_client`` and
    return the target's .torrent. Returns None when the source has no file list
    or no candidate exactly matches.
    """
    source = await source_client.torrents.get(source_torrent_id)
    if not source.files:
        logger.info("cross-seed: source torrent %d has no file list", source_torrent_id)
        return None

    candidates = await find_candidates(source, target_client, max_deep_checks=max_deep_checks)
    for candidate in candidates:
        if verify_match(source, candidate):
            torrent_file = await target_client.torrents.download(candidate.id)
            return CrossSeedResult(
                match=candidate,
                torrent_file=torrent_file,
                source_torrent_id=source_torrent_id,
                target_torrent_id=candidate.id,
            )
    return None
```

- [ ] **Step 4: Run → expect PASS** (4 passed). Then the whole file + full suite:

Run: `uv run pytest tests/test_crossseed.py -q` (expect all green) and `uv run pytest --ignore=tests/integration -q`.

- [ ] **Step 5: Quality gate on changed files, then commit**

Run: `uv run ruff check src/pygazelle/crossseed.py tests/test_crossseed.py tests/support.py` + `uv run ruff format ...` + `uv run basedpyright` (whole project — must be 0/0/0).

```bash
git add src/pygazelle/crossseed.py tests/test_crossseed.py
git commit -F - <<'EOF'
feat(crossseed): end-to-end cross_seed orchestrator

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 6: Synchronous surface

**Files:**
- Modify: `src/pygazelle/sync.py`
- Test: `tests/test_crossseed_sync.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_crossseed_sync.py`:

```python
from pygazelle.client import GazelleClient
from pygazelle.crossseed import CrossSeedResult
from pygazelle.sync import GazelleSyncClient, cross_seed_sync
from tests.support import CrossSeedTransport, make_browse_group, make_browse_row, make_torrent_payload

_BASE = dict(group_id=5, group_name="Album", year=2020, artist="Band")


def test_cross_seed_sync_returns_without_await():
    files = [("01.flac", 30)]
    source_t = CrossSeedTransport(
        torrents={1: make_torrent_payload(torrent_id=1, file_path="Album [FLAC]", files=files, **_BASE)}
    )
    target_t = CrossSeedTransport(
        browse_results=[make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020,
                                          torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)])],
        torrents={20: make_torrent_payload(torrent_id=20, file_path="Album [FLAC]", files=files, **_BASE)},
        download_bytes=b"sync-torrent",
    )
    source = GazelleSyncClient(GazelleClient(source_t))  # pyright: ignore[reportArgumentType]
    target = GazelleSyncClient(GazelleClient(target_t))  # pyright: ignore[reportArgumentType]
    try:
        result = cross_seed_sync(source, 1, target)
        assert isinstance(result, CrossSeedResult)
        assert result.torrent_file == b"sync-torrent"
        assert result.target_torrent_id == 20
    finally:
        source.close()
        target.close()
```

- [ ] **Step 2: Run → expect FAIL** (`cannot import name 'cross_seed_sync'`).

Run: `uv run pytest tests/test_crossseed_sync.py -q`

- [ ] **Step 3: Add `cross_seed_sync` to `src/pygazelle/sync.py`**

Add this module-level function to `sync.py` (after the `GazelleSyncClient` class is fine; it uses the sync clients' internals). Add a return-type import under `TYPE_CHECKING` if not present:

At the top of `sync.py`, ensure there is a `TYPE_CHECKING` import block (add if missing):
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .crossseed import CrossSeedResult
```

Then add:
```python
def cross_seed_sync(
    source_client: GazelleSyncClient,
    source_torrent_id: int,
    target_client: GazelleSyncClient,
    *,
    max_deep_checks: int = 5,
) -> CrossSeedResult | None:
    """Synchronous cross-seed: runs the async cross_seed on the source client's
    background loop. Returns the result (or None) directly, no await.
    """
    from .crossseed import cross_seed

    return source_client._bg.run(
        cross_seed(
            source_client._async,
            source_torrent_id,
            target_client._async,
            max_deep_checks=max_deep_checks,
        )
    )
```

Note: accessing `_bg` / `_async` is internal to the package (sync.py already owns these). If basedpyright flags private access from a module-level function in the same module, it will not — they are attributes of `GazelleSyncClient` defined in this file.

- [ ] **Step 4: Run → expect PASS** (1 passed).

Run: `uv run pytest tests/test_crossseed_sync.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/sync.py tests/test_crossseed_sync.py
git commit -F - <<'EOF'
feat(crossseed): synchronous cross_seed_sync entry point

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 7: Public exports

**Files:**
- Modify: `src/pygazelle/__init__.py`
- Test: `tests/test_crossseed.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_crossseed.py`:

```python
def test_public_exports():
    import pygazelle

    for name in ("cross_seed", "find_candidates", "verify_match", "CrossSeedResult", "cross_seed_sync"):
        assert hasattr(pygazelle, name), name
        assert name in pygazelle.__all__, name
```

- [ ] **Step 2: Run → expect FAIL** (`module 'pygazelle' has no attribute 'cross_seed'`).

Run: `uv run pytest tests/test_crossseed.py -k exports -q`

- [ ] **Step 3: Add exports to `src/pygazelle/__init__.py`**

Add imports after the existing ones:
```python
from .crossseed import CrossSeedResult, cross_seed, find_candidates, verify_match
from .sync import cross_seed_sync
```
(There is already a `from .sync import ...` line — extend it to also import `cross_seed_sync`, or add the separate line above.)

Add to `__all__`:
```python
    "cross_seed",
    "find_candidates",
    "verify_match",
    "CrossSeedResult",
    "cross_seed_sync",
```

- [ ] **Step 4: Run → expect PASS**, then confirm import + full suite.

Run: `uv run pytest tests/test_crossseed.py -k exports -q` then `uv run python -c "import pygazelle; print('ok')"` and `uv run pytest --ignore=tests/integration -q`.

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/__init__.py tests/test_crossseed.py
git commit -F - <<'EOF'
feat(crossseed): export public cross-seed API

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 8: Integration test, README, full quality gate

**Files:**
- Create: `tests/integration/test_crossseed_live.py`
- Modify: `README.md`

- [ ] **Step 1: Opt-in cross-tracker integration test**

First read `tests/integration/conftest.py` + an existing integration test to match the credential-fixture/skip pattern. A cross-seed live test needs BOTH trackers' credentials, so it must skip unless both are present. Create `tests/integration/test_crossseed_live.py` mirroring that pattern; a reasonable shape (adapt to the actual conftest fixtures):

```python
import os

import pytest

from pygazelle.client import OrpheusClient, RedactedClient
from pygazelle.crossseed import cross_seed

ORPHEUS_API_KEY = os.getenv("ORPHEUS_API_KEY")
REDACTED_API_KEY = os.getenv("REDACTED_API_KEY")
SOURCE_TORRENT_ID = os.getenv("CROSS_SEED_SOURCE_TORRENT_ID")


@pytest.mark.skipif(
    not (ORPHEUS_API_KEY and REDACTED_API_KEY and SOURCE_TORRENT_ID),
    reason="needs both tracker keys and CROSS_SEED_SOURCE_TORRENT_ID",
)
async def test_cross_seed_live_read_only():
    source = OrpheusClient(api_key=ORPHEUS_API_KEY, max_retries=0)
    target = RedactedClient(api_key=REDACTED_API_KEY, max_retries=0)
    try:
        result = await cross_seed(source, int(SOURCE_TORRENT_ID), target, max_deep_checks=3)
        # May be None (no match); just assert the call completes and the type is right.
        assert result is None or result.confidence == "exact"
    finally:
        await source.aclose()
        await target.aclose()
```

> Verify `max_retries` is a valid client kwarg (it is, per `transport.py`). If the integration suite uses shared fixtures for clients, use those instead. Read-only: only `get`/`browse`/`download` are issued, `max_retries=0`.

Run: `uv run pytest tests/integration/test_crossseed_live.py -q` → expect `1 skipped` (unless all three env vars are set). Never a failure.

- [ ] **Step 2: README usage example**

Find the usage section in `README.md` and add (match the surrounding heading level):

````markdown
### Cross-seeding a release to another tracker

```python
from pygazelle import OrpheusClient, RedactedClient, cross_seed

async with OrpheusClient(api_key="...") as source, RedactedClient(api_key="...") as target:
    result = await cross_seed(source, source_torrent_id=12345, target_client=target)
    if result:
        # Same release found on the target tracker; write its .torrent and add to your client.
        with open("match.torrent", "wb") as fh:
            fh.write(result.torrent_file)
        print("matched target torrent", result.target_torrent_id)
    else:
        print("no exact match on the target tracker")
```

A synchronous `cross_seed_sync(source_sync_client, source_torrent_id, target_sync_client)` is also available.
````

Note: the README example calls `cross_seed(source, source_torrent_id=..., target_client=target)`. Ensure the positional/keyword shape matches the implemented signature `cross_seed(source_client, source_torrent_id, target_client, *, max_deep_checks=5)` — adjust the example to use positional args if needed so it is copy-paste correct.

- [ ] **Step 3: Full quality gate**

Run each; all clean:
```bash
uv run pytest --ignore=tests/integration
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run codespell
```
Expected: tests pass (integration/model skips OK); ruff 0 errors; basedpyright 0 errors / 0 warnings (WHOLE project — fix any test-file issues, e.g. use `# pyright: ignore[reportArgumentType]` for fake-transport client construction, not mypy-style `# type: ignore[arg-type]`); codespell clean.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_crossseed_live.py README.md
git commit -F - <<'EOF'
test(crossseed): opt-in live test; docs: cross-seed usage example

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Self-Review (completed during planning)

**Spec coverage** (delta `specs/cross-seed/spec.md`):

| Requirement | Task |
|---|---|
| Cross-seed a source release to a target tracker (match / no-match / no-filelist) | Task 5 |
| Metadata-based candidate discovery (search, pre-filter, groupname fallback) | Task 4 |
| Strict file-list verification (any-order pass, folder-diff reject, size/path reject) | Task 3 |
| Cross-seed result contents (match, bytes, ids, confidence=exact) | Tasks 1 + 5 |
| Rate-limit-safe candidate evaluation (pre-filter bounds fetches, truncation logged) | Task 4 (`test_find_candidates_prefilters_wrong_format`, `_caps_deep_checks`) |
| Synchronous cross-seed surface | Task 6 |

**Placeholder scan:** No TBD/"handle edge cases"/"similar to". The one `match=None  # type: ignore` in Task 1's test is an intentional minimal-construction check (the dataclass does not validate types); Task 5 exercises a real `Torrent` match. The integration test (Task 8) is intentionally environment-gated.

**Type consistency:** signatures are stable across tasks — `verify_match(source: Torrent, candidate: Torrent) -> bool`; `find_candidates(source: Torrent, target_client, *, max_deep_checks=5) -> list[Torrent]`; `cross_seed(source_client, source_torrent_id, target_client, *, max_deep_checks=5) -> CrossSeedResult | None`; `cross_seed_sync(source_client, source_torrent_id, target_client, *, max_deep_checks=5)`; `CrossSeedResult(match, torrent_file, source_torrent_id, target_torrent_id, confidence="exact")`. Field/attr names match the real models (`Torrent.files[].path/.size`, `.file_path`, `.group.artists[].name`, `BrowseTorrent.torrent_id/.size/.file_count/.format/.encoding/.media`).
