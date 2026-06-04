# Cross-Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A two-phase cross-upload feature — a read-only `prepare_upload` (map source metadata to the target schema, detect duplicates, validate; no write) and an explicit `submit_upload` (the single live `action=upload` POST), gated against re-uploading an existing release.

**Architecture:** A new module `src/pygazelle/crossupload.py` with `map_metadata` (pure mapping + tables), `duplicate_check` (reuses cross-seed search/`verify_match`), `prepare_upload` (orchestrator → `UploadDraft`), and `submit_upload` (validates required fields + exact-duplicate gate, POSTs multipart via `request_write`). Plus `UserResource.announce_url()`, a per-tracker announce host on the transport, and a sync surface. The `.torrent` is caller-supplied opaque bytes.

**Tech Stack:** Python 3.11+, httpx, pydantic v2, pytest (`asyncio_mode = "auto"`), uv, ruff, basedpyright.

---

## CRITICAL SAFETY RULE (read first)

`submit_upload` performs a **live upload that creates a torrent on a real tracker**. **No automated test may ever call `submit_upload` against a live tracker.** Every `submit_upload` test uses a mock/stub transport that records the request and returns a canned response. The only permitted live test is an opt-in, read-only check of `announce_url`/`duplicate_check` — never a real upload.

## Tracker-specific UNKNOWNS (isolate + verify; do not invent silently)

These are not fully known without the Gazelle API docs/fixtures. Isolate each as a named constant/table so it can be corrected without restructuring, and leave a `# VERIFY:` comment. Tests assert the *logic*, not these exact values.

1. **Announce hosts** per tracker (Orpheus vs Redacted) — used to build the announce URL.
2. **`action=upload` form field names + required set** per tracker — the riskiest unknown.
3. **Release-type id mapping** (Orpheus ↔ Redacted numeric ids).
4. **Upload response shape** (where the new torrent/group id + URL live).

When a real value is unknown, use a clearly-named constant with a `# VERIFY` comment and a representative value; the logic and tests are built around the structure, not the literal.

## Background (existing APIs)

- `await client.torrents.get(id) -> Torrent`; `Torrent.group` (`TorrentGroup`: `name`, `year`, `tags`, `release_type: int|None`, `artists: list[TorrentArtist(.name)]`), `Torrent.format/encoding/media/file_path/files`.
- `await client.torrents.search(query, **params) -> list[TorrentResult]` (browse).
- Cross-seed (already shipped, importable from `pygazelle.crossseed`): `find_candidates(source, target_client, *, max_deep_checks=5)`, `verify_match(source, candidate)`.
- `transport.request_write(action, *, data=None, files=None, params=None, include_auth_key=True) -> dict` (POST + authkey; multipart via `files=`).
- `transport.request("index")` returns the index response (includes `passkey`, currently dropped by the `User` model).
- Sync (`sync.py`): `GazelleSyncClient._async` (async client) + `._bg.run(coro)`.
- Conventions: `from __future__ import annotations`; ruff line-length 100; basedpyright strict-clean **whole project** (`uv run basedpyright`); tests `async def test_*` (no decorator); `tests/support.py` importable as `tests.support`. Run tests `uv run pytest ...` (ignore the `VIRTUAL_ENV` warning).
- No import cycle: `crossupload.py` imports `GazelleClient` only under `TYPE_CHECKING`; `sync`→`crossupload` (runtime, deferred in function body); nothing else imports `crossupload`.

## File Structure

- **Create** `src/pygazelle/crossupload.py` — dataclasses, mapping tables, `map_metadata`, `duplicate_check`, `prepare_upload`, `submit_upload`.
- **Modify** `src/pygazelle/models/user.py` — add `passkey: str | None = None` to `User`.
- **Modify** `src/pygazelle/transport.py` — add `announce_host` to `TransportOptions` + `GazelleTransport`.
- **Modify** `src/pygazelle/client.py` — set the announce host in `OrpheusClient`/`RedactedClient`.
- **Modify** `src/pygazelle/resources/user.py` — add `announce_url()`.
- **Modify** `src/pygazelle/sync.py` — `prepare_upload_sync` / `submit_upload_sync`.
- **Modify** `src/pygazelle/__init__.py` — exports.
- **Modify** `tests/support.py` — add `UploadTransport` fake + builders.
- **Create** `tests/test_crossupload.py`, `tests/test_crossupload_sync.py`.
- **Modify** `README.md` — cross-upload example.

---

## Task 1: Dataclasses + module skeleton

**Files:** Create `src/pygazelle/crossupload.py`; Test `tests/test_crossupload.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_crossupload.py`:

```python
from __future__ import annotations

from pygazelle.crossupload import DuplicateMatch, UploadDraft, UploadResult


def test_dataclasses_hold_fields():
    dup = DuplicateMatch(torrent_id=7, group_id=3, kind="exact", name="Band - Album")
    draft = UploadDraft(
        form={"title": "Album"},
        unmapped=["release_type"],
        warnings=["release type 21 has no equivalent"],
        duplicates=[dup],
        torrent_file=b"data",
        source_torrent_id=1,
        target_tracker="redacted",
    )
    assert draft.form["title"] == "Album"
    assert draft.unmapped == ["release_type"]
    assert draft.duplicates[0].kind == "exact"
    # UploadDraft is mutable: caller fills gaps
    draft.form["release_type"] = 1
    assert draft.form["release_type"] == 1

    res = UploadResult(torrent_id=99, group_id=42, url="https://red/torrents.php?id=42")
    assert res.torrent_id == 99
```

- [ ] **Step 2: Run → FAIL** (`No module named 'pygazelle.crossupload'`). `uv run pytest tests/test_crossupload.py -q`

- [ ] **Step 3: Create `src/pygazelle/crossupload.py`**

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from .crossseed import find_candidates, verify_match
from .errors import GazelleError
from .models.torrents import Torrent

if TYPE_CHECKING:
    from .client import GazelleClient

logger = logging.getLogger("pygazelle.crossupload")

TrackerKind = Literal["orpheus", "redacted"]
DuplicateKind = Literal["exact", "possible"]


@dataclass(frozen=True)
class DuplicateMatch:
    torrent_id: int
    group_id: int
    kind: DuplicateKind
    name: str


@dataclass
class UploadDraft:
    """Mutable: the caller fills `form` for any `unmapped` fields before submit."""

    form: dict[str, Any]
    unmapped: list[str]
    warnings: list[str]
    duplicates: list[DuplicateMatch]
    torrent_file: bytes
    source_torrent_id: int
    target_tracker: TrackerKind


@dataclass(frozen=True)
class UploadResult:
    torrent_id: int
    group_id: int
    url: str
```

(`find_candidates`/`verify_match`/`GazelleError`/`GazelleClient` are used by later tasks. If ruff F401 flags any as unused now, add `# noqa: F401  # used by later cross-upload functions`; a later task that uses them removes the noqa.)

- [ ] **Step 4: Run → PASS.** `uv run pytest tests/test_crossupload.py -q`
- [ ] **Step 5: Commit** `feat(crossupload): dataclasses and module skeleton` (with the Co-Authored-By trailer used elsewhere in this repo).

---

## Task 2: Announce URL

**Files:** Modify `models/user.py`, `transport.py`, `client.py`, `resources/user.py`; Test `tests/test_crossupload.py`.

- [ ] **Step 1: Determine the per-tracker announce hosts.** `# VERIFY` against the trackers: the announce host is NOT the API host. Record the confirmed values; if unverifiable now, use the best-known values with a `# VERIFY` comment (Orpheus and Redacted each publish an announce URL in the user's profile/index — confirm the host).

- [ ] **Step 2: Write the failing test**

Append to `tests/test_crossupload.py`:

```python
from pygazelle.client import GazelleClient
from tests.support import UploadTransport


async def test_announce_url_built_from_passkey_and_host():
    transport = UploadTransport(passkey="abc123", announce_host="flacsfor.me")
    client = GazelleClient(transport)  # pyright: ignore[reportArgumentType]
    url = await client.user.announce_url()
    assert url == "https://flacsfor.me/abc123/announce"
```

- [ ] **Step 3: Implement**

In `src/pygazelle/models/user.py`, add to `User`:
```python
    passkey: str | None = None
```

In `src/pygazelle/transport.py`: add `announce_host: str | None` to the `TransportOptions` TypedDict and to `GazelleTransport.__init__` (store `self.announce_host = announce_host`). Follow how `api_key_prefix`/`user_agent` are threaded.

In `src/pygazelle/client.py`: pass the announce host in the subclasses, e.g. `OrpheusClient` → `kwargs.setdefault("announce_host", ORPHEUS_ANNOUNCE_HOST)` and `RedactedClient` → `REDACTED_ANNOUNCE_HOST`, with module constants near the base URLs:
```python
# VERIFY announce hosts against each tracker (NOT the API host).
ORPHEUS_ANNOUNCE_HOST = "home.opsfet.ch"
REDACTED_ANNOUNCE_HOST = "flacsfor.me"
```

In `src/pygazelle/resources/user.py`, add:
```python
    async def announce_url(self) -> str:
        """The current user's announce URL on this tracker (passkey + announce host)."""
        me = await self.me()
        host = self._transport.announce_host
        if not me.passkey or not host:
            raise GazelleError("announce URL unavailable: missing passkey or announce host")
        return f"https://{host}/{me.passkey}/announce"
```
(Import `GazelleError` from `..errors`. Confirm `self._transport.announce_host` is typed — add `announce_host` to the `SupportsTransport` protocol in `resources/base.py`/`transport.py` if basedpyright requires it.)

- [ ] **Step 4: Run → PASS.** `uv run pytest tests/test_crossupload.py -k announce -q`
- [ ] **Step 5: Commit** `feat(crossupload): expose target announce_url (passkey + per-tracker host)`.

---

## Task 3: Test fakes (`UploadTransport`)

**Files:** Modify `tests/support.py`.

- [ ] **Step 1: Append to `tests/support.py`**

```python
class UploadTransport:
    """Fake transport for cross-upload tests.

    index_passkey -> returned as the index 'passkey'; announce_host stored for
    UserResource.announce_url. torrents/browse mirror CrossSeedTransport for
    duplicate detection. request_write records the upload call and returns
    upload_response. No real network; submit tests assert on `self.writes`.
    """

    def __init__(
        self,
        *,
        passkey: str | None = None,
        announce_host: str | None = None,
        index: dict[str, Any] | None = None,
        torrents: dict[int, dict[str, Any]] | None = None,
        browse_results: list[dict[str, Any]] | None = None,
        upload_response: dict[str, Any] | None = None,
        user_id: int = 1,
    ) -> None:
        self.announce_host = announce_host
        self._passkey = passkey
        self._index = index
        self._torrents = torrents or {}
        self._browse_results = browse_results or []
        self._upload_response = upload_response or {}
        self._user_id = user_id
        self.writes: list[dict[str, Any]] = []

    async def request(self, action: str, **params: Any) -> Any:
        if action == "index":
            return self._index or {"id": self._user_id, "username": "tester", "passkey": self._passkey}
        if action == "torrent":
            from pygazelle.errors import GazelleNotFoundError

            tid = params["id"]
            if tid not in self._torrents:
                raise GazelleNotFoundError(f"torrent {tid} not found")
            return self._torrents[tid]
        if action == "browse":
            return {"results": self._browse_results}
        raise AssertionError(f"unexpected read action: {action}")

    async def request_write(
        self,
        action: str,
        *,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, Any] | None = None,
        include_auth_key: bool = True,
    ) -> Any:
        self.writes.append({"action": action, "data": data, "files": files, "params": params})
        return self._upload_response

    async def download(self, torrent_id: int) -> bytes:  # pragma: no cover - unused here
        return b""

    async def aclose(self) -> None:  # for GazelleSyncClient.close()
        pass
```

- [ ] **Step 2: Sanity import.** `uv run python -c "from tests.support import UploadTransport; print('ok')"`
- [ ] **Step 3: Commit** `test(crossupload): add UploadTransport fake`.

> Reuse the cross-seed helpers `make_torrent_payload` / `make_browse_group` / `make_browse_row` (already in `tests/support.py`) to build source torrents and duplicate candidates.

---

## Task 4: `map_metadata` (9m7)

**Files:** Modify `src/pygazelle/crossupload.py`; Test `tests/test_crossupload.py`.

- [ ] **Step 1: Failing tests**

Append to `tests/test_crossupload.py`:

```python
from pygazelle.crossupload import map_metadata
from pygazelle.models.torrents import Torrent
from tests.support import make_torrent_payload


def _src(release_type: int = 1, tags=("rock",)) -> Torrent:
    p = make_torrent_payload(
        torrent_id=1, group_id=5, group_name="Album", year=2020, artist="Band",
        file_path="Album [FLAC]", files=[("01.flac", 30)],
    )
    p["group"]["releaseType"] = release_type
    p["group"]["tags"] = list(tags)
    return Torrent.model_validate({**p["torrent"], "group": p["group"]})


def test_map_metadata_direct_fields():
    mapped = map_metadata(_src(), "redacted")
    assert mapped.fields["title"] == "Album"
    assert mapped.fields["year"] == 2020
    assert mapped.fields["artists"] == ["Band"]
    assert mapped.fields["format"] == "FLAC"


def test_map_metadata_release_type_table_hit():
    # release_type 1 maps for redacted (see RELEASE_TYPE_MAP)
    mapped = map_metadata(_src(release_type=1), "redacted")
    assert "release_type" not in mapped.unmapped
    assert "release_type" in mapped.fields


def test_map_metadata_release_type_miss_flags_unmapped():
    mapped = map_metadata(_src(release_type=9999), "redacted")
    assert "release_type" in mapped.unmapped
    assert any("release type" in w.lower() for w in mapped.warnings)
    assert "release_type" not in mapped.fields


def test_map_metadata_tags_warned():
    mapped = map_metadata(_src(tags=("rock", "obscure.subgenre")), "redacted")
    assert mapped.fields.get("tags")  # tags carried through
    # divergent/uncertain tags produce a warning to review
    assert any("tag" in w.lower() for w in mapped.warnings)
```

- [ ] **Step 2: Run → FAIL** (`cannot import name 'map_metadata'`). `uv run pytest tests/test_crossupload.py -k map_metadata -q`

- [ ] **Step 3: Implement**

Add to `src/pygazelle/crossupload.py`:

```python
@dataclass
class MappedForm:
    fields: dict[str, Any] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# VERIFY: Orpheus<->Redacted release-type ids. Keyed by source release_type int,
# valued per target tracker. Missing entries -> unmapped (safe).
RELEASE_TYPE_MAP: dict[TrackerKind, dict[int, int]] = {
    "redacted": {1: 1, 3: 3, 5: 5, 6: 6, 7: 7, 9: 9, 11: 11, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 21: 21},
    "orpheus": {1: 1, 3: 3, 5: 5, 6: 6, 7: 7, 9: 9, 11: 11, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 21: 21},
}

# VERIFY: the target upload form field names + required set per tracker.
REQUIRED_FIELDS: dict[TrackerKind, tuple[str, ...]] = {
    "redacted": ("artists", "title", "year", "release_type", "format", "bitrate", "media"),
    "orpheus": ("artists", "title", "year", "release_type", "format", "bitrate", "media"),
}


def map_metadata(source: Torrent, target: TrackerKind) -> MappedForm:
    """Best-effort map of a source release's metadata to the target upload schema.
    Confident fields go to `fields`; anything unmappable/uncertain is recorded in
    `unmapped` + `warnings` and never guessed.
    """
    out = MappedForm()
    group = source.group
    if group is not None:
        out.fields["title"] = group.name
        out.fields["year"] = group.year
        out.fields["artists"] = [a.name for a in group.artists]
        if group.tags:
            out.fields["tags"] = list(group.tags)
            out.warnings.append(
                "tags carried over verbatim; review against the target's tag rules"
            )
        rt = group.release_type
        mapped_rt = RELEASE_TYPE_MAP.get(target, {}).get(rt) if rt is not None else None
        if mapped_rt is not None:
            out.fields["release_type"] = mapped_rt
        else:
            out.unmapped.append("release_type")
            out.warnings.append(f"release type {rt} has no {target} equivalent; set it manually")
    # Direct technical fields.
    out.fields["format"] = source.format
    out.fields["bitrate"] = source.encoding  # Gazelle 'bitrate' carries the encoding value
    out.fields["media"] = source.media
    return out
```

- [ ] **Step 4: Run → PASS.** `uv run pytest tests/test_crossupload.py -k map_metadata -q`
- [ ] **Step 5: Commit** `feat(crossupload): best-effort metadata mapping with review flags (9m7)`.

---

## Task 5: `duplicate_check` (xn1)

**Files:** Modify `src/pygazelle/crossupload.py`; Test `tests/test_crossupload.py`.

- [ ] **Step 1: Failing tests**

Append:

```python
from pygazelle.crossupload import DuplicateMatch, duplicate_check
from tests.support import UploadTransport, make_browse_group, make_browse_row


def _client(t):
    return GazelleClient(t)  # pyright: ignore[reportArgumentType]


async def test_duplicate_check_exact():
    files = [("01.flac", 30)]
    source = _src()  # Album [FLAC], 1 file, 30 bytes (from Task 4 helper)
    target = UploadTransport(
        browse_results=[make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020,
                          torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)])],
        torrents={20: make_torrent_payload(torrent_id=20, group_id=9, group_name="Album", year=2020,
                   artist="Band", file_path="Album [FLAC]", files=files)},
    )
    dupes = await duplicate_check(source, _client(target))
    assert [(d.torrent_id, d.kind) for d in dupes] == [(20, "exact")]


async def test_duplicate_check_possible():
    source = _src()
    target = UploadTransport(
        browse_results=[make_browse_group(group_id=9, group_name="Album", artist="Band", year=2020,
                          torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)])],
        # candidate has a different file path -> not exact, but same group -> possible
        torrents={20: make_torrent_payload(torrent_id=20, group_id=9, group_name="Album", year=2020,
                   artist="Band", file_path="DIFFERENT", files=[("01.flac", 30)])},
    )
    dupes = await duplicate_check(source, _client(target))
    assert [(d.torrent_id, d.kind) for d in dupes] == [(20, "possible")]


async def test_duplicate_check_none():
    source = _src()
    target = UploadTransport(browse_results=[])
    assert await duplicate_check(source, _client(target)) == []
```

- [ ] **Step 2: Run → FAIL.** `uv run pytest tests/test_crossupload.py -k duplicate_check -q`

- [ ] **Step 3: Implement** (reuses cross-seed; remove the `find_candidates`/`verify_match` noqa from Task 1 if present):

```python
async def duplicate_check(source: Torrent, target_client: GazelleClient) -> list[DuplicateMatch]:
    """Search the target for releases matching the source; classify each as an
    exact duplicate (file-list match) or a possible duplicate (same group/metadata)."""
    candidates = await find_candidates(source, target_client)
    matches: list[DuplicateMatch] = []
    for cand in candidates:
        kind: DuplicateKind = "exact" if verify_match(source, cand) else "possible"
        group_id = cand.group.id if cand.group else 0
        name = cand.group.name if cand.group else ""
        matches.append(
            DuplicateMatch(torrent_id=cand.id, group_id=group_id, kind=kind, name=name)
        )
    return matches
```

> Note: `find_candidates` already pre-filters on format/size/etc., so `possible` here means "same metadata + same technical attributes but a different file tree." That is the useful signal for upload dup-detection. (If broader group-level detection is wanted later, widen the search; out of scope now.)

- [ ] **Step 4: Run → PASS.** `uv run pytest tests/test_crossupload.py -k duplicate_check -q`
- [ ] **Step 5: Commit** `feat(crossupload): duplicate detection on the target (xn1)`.

---

## Task 6: `prepare_upload` orchestrator (read-only)

**Files:** Modify `src/pygazelle/crossupload.py`; Test `tests/test_crossupload.py`.

- [ ] **Step 1: Failing tests**

Append:

```python
from pygazelle.crossupload import UploadDraft, prepare_upload


def _tracker_of(client) -> str:
    # helper mirrors how prepare_upload derives the target kind in tests
    return "redacted"


async def test_prepare_upload_assembles_draft_no_writes():
    files = [("01.flac", 30)]
    source_t = UploadTransport(
        torrents={1: make_torrent_payload(torrent_id=1, group_id=5, group_name="Album", year=2020,
                   artist="Band", file_path="Album [FLAC]", files=files)}
    )
    # add a release type the table maps
    src_payload = source_t._torrents[1]
    src_payload["group"]["releaseType"] = 1
    target_t = UploadTransport(browse_results=[])  # no dupes
    draft = await prepare_upload(_client(source_t), 1, _client(target_t), torrent_file=b"tbytes")
    assert isinstance(draft, UploadDraft)
    assert draft.torrent_file == b"tbytes"
    assert draft.form["title"] == "Album"
    assert draft.duplicates == []
    # READ-ONLY: prepare must not write to the target
    assert target_t.writes == []


async def test_prepare_upload_source_not_found_raises():
    import pytest
    from pygazelle.errors import GazelleNotFoundError

    source_t = UploadTransport(torrents={})  # torrent 1 absent -> get raises
    target_t = UploadTransport()
    with pytest.raises(GazelleNotFoundError):
        await prepare_upload(_client(source_t), 1, _client(target_t), torrent_file=b"x")
```

- [ ] **Step 2: Run → FAIL.** `uv run pytest tests/test_crossupload.py -k prepare_upload -q`

- [ ] **Step 3: Implement.** prepare_upload derives the target tracker kind from the client and assembles the draft:

```python
def _tracker_kind(client: GazelleClient) -> TrackerKind:
    # Derive from the announce host (set per tracker), avoiding an isinstance import cycle.
    host = getattr(client._transport, "announce_host", None)  # pyright: ignore[reportPrivateUsage]
    if host and "opsfet" in host:
        return "orpheus"
    return "redacted"


async def prepare_upload(
    source_client: GazelleClient,
    source_torrent_id: int,
    target_client: GazelleClient,
    *,
    torrent_file: bytes,
) -> UploadDraft:
    """Read-only: map metadata + detect duplicates + build an UploadDraft. No write."""
    source = await source_client.torrents.get(source_torrent_id)
    target = _tracker_kind(target_client)
    mapped = map_metadata(source, target)
    try:
        duplicates = await duplicate_check(source, target_client)
    except GazelleError as exc:  # a failing dup search must not abort prep
        duplicates = []
        mapped.warnings.append(f"duplicate check failed: {exc}")
    return UploadDraft(
        form=mapped.fields,
        unmapped=mapped.unmapped,
        warnings=mapped.warnings,
        duplicates=duplicates,
        torrent_file=torrent_file,
        source_torrent_id=source_torrent_id,
        target_tracker=target,
    )
```

> If basedpyright objects to `client._transport` private access, add an `announce_host` accessor or include it in the transport protocol; keep the `# pyright: ignore[reportPrivateUsage]` only if necessary and accurate.

- [ ] **Step 4: Run → PASS** + full file. `uv run pytest tests/test_crossupload.py -q`
- [ ] **Step 5: Commit** `feat(crossupload): prepare_upload orchestrator (read-only)`.

---

## Task 7: `submit_upload` (validation + exact-dupe gate + multipart POST) (xn1)

**Files:** Modify `src/pygazelle/crossupload.py`; Test `tests/test_crossupload.py`.

- [ ] **Step 1: Failing tests**

Append:

```python
from pygazelle.crossupload import UploadResult, submit_upload


def _complete_draft(target="redacted", duplicates=None) -> UploadDraft:
    return UploadDraft(
        form={"artists": ["Band"], "title": "Album", "year": 2020, "release_type": 1,
              "format": "FLAC", "bitrate": "Lossless", "media": "CD"},
        unmapped=[], warnings=[], duplicates=duplicates or [],
        torrent_file=b"tbytes", source_torrent_id=1, target_tracker=target,
    )


async def test_submit_refuses_missing_required_field():
    import pytest
    draft = _complete_draft()
    del draft.form["title"]  # required field missing
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    with pytest.raises(ValueError) as ei:
        await submit_upload(_client(target), draft)
    assert "title" in str(ei.value)
    assert target.writes == []  # never POSTed


async def test_submit_refuses_on_exact_duplicate():
    import pytest
    draft = _complete_draft(duplicates=[DuplicateMatch(torrent_id=20, group_id=9, kind="exact", name="x")])
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    with pytest.raises(ValueError):
        await submit_upload(_client(target), draft)
    assert target.writes == []


async def test_submit_allows_exact_duplicate_with_override():
    draft = _complete_draft(duplicates=[DuplicateMatch(torrent_id=20, group_id=9, kind="exact", name="x")])
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    result = await submit_upload(_client(target), draft, allow_duplicate=True)
    assert isinstance(result, UploadResult)
    assert len(target.writes) == 1


async def test_submit_possible_duplicate_does_not_block():
    draft = _complete_draft(duplicates=[DuplicateMatch(torrent_id=20, group_id=9, kind="possible", name="x")])
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    result = await submit_upload(_client(target), draft)
    assert result.torrent_id == 99


async def test_submit_happy_path_posts_multipart():
    draft = _complete_draft()
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    result = await submit_upload(_client(target), draft)
    assert result == UploadResult(torrent_id=99, group_id=42, url=result.url)
    write = target.writes[0]
    assert write["action"] == "upload"
    assert write["files"] is not None  # the .torrent was attached
    # the mapped form fields were sent
    assert write["data"]["title"] == "Album"
```

- [ ] **Step 2: Run → FAIL.** `uv run pytest tests/test_crossupload.py -k submit -q`

- [ ] **Step 3: Implement**

```python
def _missing_required(draft: UploadDraft) -> list[str]:
    required = REQUIRED_FIELDS.get(draft.target_tracker, ())
    return [f for f in required if f not in draft.form or draft.form[f] in (None, "", [])]


async def submit_upload(
    target_client: GazelleClient,
    draft: UploadDraft,
    *,
    allow_duplicate: bool = False,
) -> UploadResult:
    """The live write: validate the draft, gate on exact duplicates, then POST
    action=upload. Refuses (no write) on missing required fields or an unallowed
    exact duplicate.
    """
    missing = _missing_required(draft)
    if missing:
        raise ValueError(f"cannot submit: missing required field(s): {', '.join(missing)}")
    if not allow_duplicate and any(d.kind == "exact" for d in draft.duplicates):
        raise ValueError(
            "an exact duplicate exists on the target; pass allow_duplicate=True to override"
        )

    files = [("file_input", ("upload.torrent", draft.torrent_file))]  # VERIFY upload file field name
    data = await target_client._transport.request_write(  # pyright: ignore[reportPrivateUsage]
        "upload", data=dict(draft.form), files=files
    )
    # VERIFY response keys for the new torrent/group id.
    torrent_id = int(data.get("torrentid") or data.get("torrentId") or 0)
    group_id = int(data.get("groupid") or data.get("groupId") or 0)
    return UploadResult(
        torrent_id=torrent_id,
        group_id=group_id,
        url=f"torrents.php?id={group_id}&torrentid={torrent_id}",
    )
```

> `target_client._transport` is the transport; if private-access typing complains, route through a public method or annotate. The `file_input` field name and response keys are `# VERIFY` items.

- [ ] **Step 4: Run → PASS** + full file + whole-project basedpyright. `uv run pytest tests/test_crossupload.py -q` && `uv run basedpyright`
- [ ] **Step 5: Commit** `feat(crossupload): submit_upload with required-field validation and exact-dupe gate (xn1)`.

---

## Task 8: Sync surface + exports

**Files:** Modify `src/pygazelle/sync.py`, `src/pygazelle/__init__.py`; Test `tests/test_crossupload_sync.py`, `tests/test_crossupload.py`.

- [ ] **Step 1: Failing sync test**

Create `tests/test_crossupload_sync.py`:

```python
from __future__ import annotations

from pygazelle.client import GazelleClient
from pygazelle.crossupload import UploadDraft, UploadResult
from pygazelle.sync import GazelleSyncClient, prepare_upload_sync, submit_upload_sync
from tests.support import UploadTransport, make_torrent_payload


def test_prepare_and_submit_sync_no_await():
    files = [("01.flac", 30)]
    src_payload = make_torrent_payload(torrent_id=1, group_id=5, group_name="Album", year=2020,
                                       artist="Band", file_path="Album [FLAC]", files=files)
    src_payload["group"]["releaseType"] = 1
    source = GazelleSyncClient(GazelleClient(UploadTransport(torrents={1: src_payload})))  # pyright: ignore[reportArgumentType]
    target = GazelleSyncClient(GazelleClient(UploadTransport(browse_results=[], upload_response={"torrentid": 99, "groupid": 42})))  # pyright: ignore[reportArgumentType]
    try:
        draft = prepare_upload_sync(source, 1, target, torrent_file=b"t")
        assert isinstance(draft, UploadDraft)
        # fill any required fields the mapping left out, then submit
        for fld, val in {"artists": ["Band"], "title": "Album", "year": 2020, "release_type": 1,
                         "format": "FLAC", "bitrate": "Lossless", "media": "CD"}.items():
            draft.form.setdefault(fld, val)
        result = submit_upload_sync(target, draft)
        assert isinstance(result, UploadResult)
    finally:
        source.close()
        target.close()
```

- [ ] **Step 2: Run → FAIL.** `uv run pytest tests/test_crossupload_sync.py -q`

- [ ] **Step 3: Implement in `src/pygazelle/sync.py`** (TYPE_CHECKING import for the return types; deferred runtime import in the bodies):

```python
def prepare_upload_sync(
    source_client: GazelleSyncClient,
    source_torrent_id: int,
    target_client: GazelleSyncClient,
    *,
    torrent_file: bytes,
) -> UploadDraft:
    from .crossupload import prepare_upload

    return source_client._bg.run(  # pyright: ignore[reportPrivateUsage]
        prepare_upload(
            source_client._async,  # pyright: ignore[reportPrivateUsage]
            source_torrent_id,
            target_client._async,  # pyright: ignore[reportPrivateUsage]
            torrent_file=torrent_file,
        )
    )


def submit_upload_sync(
    target_client: GazelleSyncClient,
    draft: UploadDraft,
    *,
    allow_duplicate: bool = False,
) -> UploadResult:
    from .crossupload import submit_upload

    return target_client._bg.run(  # pyright: ignore[reportPrivateUsage]
        submit_upload(target_client._async, draft, allow_duplicate=allow_duplicate)  # pyright: ignore[reportPrivateUsage]
    )
```
Add under `TYPE_CHECKING`: `from .crossupload import UploadDraft, UploadResult`.

- [ ] **Step 4: Exports test + impl.** Append to `tests/test_crossupload.py`:
```python
def test_public_exports():
    import pygazelle

    for name in ("prepare_upload", "submit_upload", "map_metadata", "duplicate_check",
                 "UploadDraft", "UploadResult", "DuplicateMatch",
                 "prepare_upload_sync", "submit_upload_sync"):
        assert hasattr(pygazelle, name), name
        assert name in pygazelle.__all__, name
```
In `src/pygazelle/__init__.py` add:
```python
from .crossupload import (
    DuplicateMatch,
    UploadDraft,
    UploadResult,
    duplicate_check,
    map_metadata,
    prepare_upload,
    submit_upload,
)
from .sync import prepare_upload_sync, submit_upload_sync
```
and the nine names to `__all__`. (Extend the existing `from .sync import ...` line.)

- [ ] **Step 5: Run → PASS** + `uv run python -c "import pygazelle; print('ok')"` + full suite + whole-project basedpyright.
- [ ] **Step 6: Commit** `feat(crossupload): sync surface and public exports`.

---

## Task 9: Safety check, README, full quality gate

**Files:** Modify `README.md`; (optional) `tests/integration/`.

- [ ] **Step 1: SAFETY audit.** Confirm by grep that no test calls `submit_upload`/`submit_upload_sync` against anything but `UploadTransport`/a stub. Do NOT add a live upload integration test. If you add any integration test, it is read-only (`announce_url`/`duplicate_check`), creds-gated, and never calls submit.

- [ ] **Step 2: README example** — add a "Cross-uploading a release" section showing the prepare → review (`draft.unmapped`/`draft.duplicates`) → fill → submit flow and the `announce_url()` helper. Make it copy-paste correct against the implemented signatures.

- [ ] **Step 3: Full quality gate** (each clean):
```bash
uv run pytest --ignore=tests/integration
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run codespell
```

- [ ] **Step 4: Commit** `test(crossupload): safety audit; docs: cross-upload usage example`.

---

## Self-Review (completed during planning)

**Spec coverage** (delta `specs/cross-upload/spec.md`):

| Requirement | Task |
|---|---|
| Two-phase prepare (no write) + submit | Task 6 (no-write asserted) + Task 7 |
| Best-effort mapping with review flags | Task 4 |
| Duplicate detection (exact/possible/none) | Task 5 |
| Exact-duplicate submit gate (+ override, possible doesn't block) | Task 7 |
| Required-field validation before submit | Task 7 |
| Caller-supplied opaque `.torrent` + announce URL | Task 2 (announce) + Tasks 6/7 (opaque bytes attached, never parsed) |
| Synchronous surface | Task 8 |

**Placeholder scan:** No "TBD/handle edge cases". `# VERIFY` markers are deliberate, isolated tracker-data callouts (announce hosts, upload field names, release-type ids, response keys) — the design explicitly flagged these as needing verification; the logic and tests are built around structure, not the literals. No step defers code.

**Type consistency:** `map_metadata(source: Torrent, target: TrackerKind) -> MappedForm`; `duplicate_check(source, target_client) -> list[DuplicateMatch]`; `prepare_upload(source_client, source_torrent_id, target_client, *, torrent_file) -> UploadDraft`; `submit_upload(target_client, draft, *, allow_duplicate=False) -> UploadResult`; sync mirrors. `UploadDraft.form/unmapped/warnings/duplicates/torrent_file/source_torrent_id/target_tracker`; `DuplicateMatch.torrent_id/group_id/kind/name`; `UploadResult.torrent_id/group_id/url`. Consistent across tasks.

**Safety:** `submit_upload` is mock-only in every test; Task 9 audits this; no live-upload test exists.
