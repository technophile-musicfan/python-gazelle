# Upload & Snatch Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `TorrentMonitor` that auto-discovers the current user's uploaded/snatched torrents and exposes a stateless `poll()` returning typed deletion/trump/removed events via snapshot diffing, on both async and sync surfaces.

**Architecture:** A new `TorrentMonitor` (in `src/pygazelle/monitoring.py`) holds an in-memory snapshot of the user's torrent lists. Each `poll()` re-fetches the configured source lists through the **already-shipped** `UserResource.torrents(user_id, type)` endpoint, diffs torrent ids against the prior snapshot, and classifies each disappearance with **one** targeted `torrents.get_group()` lookup. The snapshot is committed only after a poll fully succeeds (atomic). New Pydantic models live in `src/pygazelle/models/monitoring.py`; a `client.monitor()` factory and a sync wrapper expose it.

**Tech Stack:** Python 3.11+, httpx (async), pydantic v2, pytest (`asyncio_mode = "auto"`), uv, ruff, basedpyright.

---

## Background the implementer needs

- **The endpoint already exists.** `UserResource.torrents(user_id, type, limit, offset)` (`src/pygazelle/resources/user.py:33`) wraps the `user_torrents` action and returns `list[UserTorrent]`. The response is keyed under the requested type, e.g. `{"uploaded": [...], "total": N}`. **Do not re-implement it.**
- **`UserTorrent` fields** (`src/pygazelle/models/user.py:76`): `group_id`, `torrent_id`, `name` (release name — there is **no** `group_name`), and optional `torrent_size`, `artist_id`, `artist_name`.
- **Classification primitive.** `client.torrents.get_group(group_id)` (`src/pygazelle/resources/torrents.py:17`) returns a `TorrentGroup` whose `.torrents` is `list[Torrent]`, each with `.id`. A **deleted group raises `GazelleNotFoundError`** (transport.py:233 maps HTTP 404 → `GazelleNotFoundError`).
- **User id.** `client.user.me()` returns a `User` with `.id` (`src/pygazelle/models/user.py:20`).
- **Models** extend `GazelleModel` (`src/pygazelle/models/base.py`): pydantic v2, `alias_generator=to_camel`, `populate_by_name=True`, `extra="ignore"`. Fields are snake_case; no per-field alias needed. Every module starts with `from __future__ import annotations`.
- **Layering rule:** models must not import from `resources/` or `client.py`. The monitor (`monitoring.py`) may import the client only under `TYPE_CHECKING`.
- **Tests:** `asyncio_mode = "auto"` — write `async def test_*` directly, no decorator. Run unit/model tests with `uv run pytest --ignore=tests/integration`.

## File Structure

- **Create** `src/pygazelle/models/monitoring.py` — `MonitoredTorrent`, `MonitorSnapshot`, `TorrentChangeEvent`.
- **Create** `src/pygazelle/monitoring.py` — `TorrentMonitor` engine.
- **Create** `tests/support.py` — shared `MonitorTransport` fake + `make_torrent_row` helper.
- **Create** `tests/models/test_monitoring.py` — model tests.
- **Create** `tests/test_monitoring.py` — `TorrentMonitor` unit tests.
- **Create** `tests/test_monitoring_sync.py` — sync surface test.
- **Create** `tests/integration/test_user_torrents_live.py` — opt-in live read.
- **Modify** `src/pygazelle/models/__init__.py` — export new models.
- **Modify** `src/pygazelle/client.py` — `monitor()` factory.
- **Modify** `src/pygazelle/sync.py` — `monitor()` on `GazelleSyncClient`.
- **Modify** `src/pygazelle/__init__.py` — export `TorrentMonitor`, `TorrentChangeEvent`.
- **Modify** `devtools/capture_fixtures.py` — capture `user_torrents` fixtures.
- **Modify** `README.md` — short monitoring usage example.

---

## Task 1: Fixture-capture tooling + verification spike

> Tooling task (not TDD). Implements tasks.md §1.1–1.3. The capture itself requires live credentials and is run manually by a maintainer; the code change is committed so the capture is repeatable. **Assumption B** (do deleted/trumped torrents drop off the list?) is resolved by inspecting the captured fixtures and recorded in the change before Task 5's conditional step.

**Files:**
- Modify: `devtools/capture_fixtures.py:60-79` (insert before the artist block)

- [ ] **Step 1: Add `user_torrents` capture to `capture(...)`**

Insert this block inside `capture(...)`, after the `torrentgroup` block (after line 58) and before the artist-derivation block:

```python
        # Capture the current user's uploaded + snatched lists (action=user_torrents).
        # `index` above carries the user id under "id".
        user_id = index.get("id")
        if user_id:
            for kind in ("uploaded", "snatched"):
                user_torrents = await t.request(
                    "user_torrents", id=user_id, type=kind, limit=50, offset=0
                )
                (out / f"user_torrents_{kind}.json").write_text(
                    json.dumps({"status": "success", "response": user_torrents}, indent=2)
                )
                print(f"[{tracker}] Captured user_torrents ({kind})")
```

- [ ] **Step 2: Lint the change**

Run: `uv run ruff check devtools/capture_fixtures.py && uv run ruff format devtools/capture_fixtures.py`
Expected: no errors; file unchanged or reformatted cleanly.

- [ ] **Step 3: Commit**

```bash
git add devtools/capture_fixtures.py
git commit -m "feat(devtools): capture user_torrents fixtures (uploaded + snatched)"
```

- [ ] **Step 4 (manual, credential-gated): capture + record findings**

If tracker creds are present in `.env`, run `uv run python devtools/capture_fixtures.py` and inspect `tests/fixtures/{orpheus,redacted}/user_torrents_*.json`. Record in `openspec/changes/upload-snatch-monitoring/tasks.md` §1.3: (a) the per-tracker field names vs. the shipped `UserTorrent` model, and (b) whether a known-deleted torrent still appears in the list. If deleted torrents **linger**, mark Task 5b (below) as REQUIRED; if they **drop off**, mark it NOT NEEDED. If creds are absent, leave §1.3 open and default Task 5b to NOT NEEDED (pure snapshot-diff ships; the fallback can be added later when data justifies it).

---

## Task 2: Confirm the shipped endpoint meets the monitor's needs

> Implements tasks.md §2.6. The endpoint + model + tests already exist; this task only confirms they cover what the monitor requires (type-keyed list, `torrent_id`/`group_id`/`name` present, `limit`/`offset` accepted). No code change expected.

**Files:**
- Read: `src/pygazelle/resources/user.py:33-43`, `tests/test_client.py:300-340`, `tests/models/test_user.py`

- [ ] **Step 1: Run the existing endpoint tests**

Run: `uv run pytest tests/test_client.py -k torrents -q && uv run pytest tests/models/test_user.py -q`
Expected: PASS. Confirm a test exercises `type`/`limit`/`offset` params and that `UserTorrent` exposes `torrent_id`, `group_id`, `name`.

- [ ] **Step 2: If a gap is found, file a follow-up**

If (and only if) the endpoint cannot return `torrent_id`/`group_id`/`name` or ignores `limit`/`offset`, stop and create a Beads issue describing the gap. Otherwise proceed — no commit for this task.

---

## Task 3: Monitoring models

**Files:**
- Create: `src/pygazelle/models/monitoring.py`
- Modify: `src/pygazelle/models/__init__.py`
- Test: `tests/models/test_monitoring.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/models/test_monitoring.py`:

```python
from pygazelle.models.monitoring import (
    MonitoredTorrent,
    MonitorSnapshot,
    TorrentChangeEvent,
)


def test_change_event_holds_all_fields():
    ev = TorrentChangeEvent(
        kind="trumped",
        source="uploaded",
        torrent_id=10,
        group_id=5,
        name="Some Release",
        replacement_torrent_id=11,
    )
    assert ev.kind == "trumped"
    assert ev.source == "uploaded"
    assert ev.torrent_id == 10
    assert ev.group_id == 5
    assert ev.name == "Some Release"
    assert ev.replacement_torrent_id == 11


def test_change_event_replacement_defaults_none():
    ev = TorrentChangeEvent(
        kind="deleted", source="snatched", torrent_id=1, group_id=2, name="X"
    )
    assert ev.replacement_torrent_id is None


def test_snapshot_round_trips_through_json():
    snap = MonitorSnapshot(
        sources={
            "uploaded": {10: MonitoredTorrent(torrent_id=10, group_id=5, name="A")},
            "snatched": {20: MonitoredTorrent(torrent_id=20, group_id=6, name="B")},
        }
    )
    dumped = snap.model_dump(mode="json")
    # JSON object keys are strings; the model must coerce them back to ints.
    restored = MonitorSnapshot.model_validate(dumped)
    assert restored == snap
    assert restored.sources["uploaded"][10].name == "A"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/models/test_monitoring.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pygazelle.models.monitoring'`.

- [ ] **Step 3: Create the models**

Create `src/pygazelle/models/monitoring.py`:

```python
from __future__ import annotations

from typing import Literal

from .base import GazelleModel

ChangeKind = Literal["deleted", "trumped", "removed"]


class MonitoredTorrent(GazelleModel):
    """A single watched torrent as recorded in a monitor snapshot."""

    torrent_id: int
    group_id: int
    name: str


class MonitorSnapshot(GazelleModel):
    """The monitor's per-source view: {source: {torrent_id: MonitoredTorrent}}.

    json-serializable via ``model_dump(mode="json")``; int keys round-trip
    through string JSON keys on ``model_validate``.
    """

    sources: dict[str, dict[int, MonitoredTorrent]] = {}


class TorrentChangeEvent(GazelleModel):
    """A classified change to a previously-watched torrent."""

    kind: ChangeKind
    source: str
    torrent_id: int
    group_id: int
    name: str
    replacement_torrent_id: int | None = None
```

- [ ] **Step 4: Export the models**

In `src/pygazelle/models/__init__.py`, add the import (after the `.inbox` import, alphabetical-ish grouping is fine) and the `__all__` entries:

```python
from .monitoring import MonitoredTorrent, MonitorSnapshot, TorrentChangeEvent
```

Add to `__all__` (near the other model names):

```python
    "MonitoredTorrent",
    "MonitorSnapshot",
    "TorrentChangeEvent",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/models/test_monitoring.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/pygazelle/models/monitoring.py src/pygazelle/models/__init__.py tests/models/test_monitoring.py
git commit -m "feat(monitoring): add MonitoredTorrent, MonitorSnapshot, TorrentChangeEvent models"
```

---

## Task 4: Shared test fake (`MonitorTransport`)

> A reusable fake transport for monitor tests: serves `index`, paginated `user_torrents` (by type), and `torrentgroup` (by id, optionally 404). Lives in a non-test helper module so both `test_monitoring.py` and `test_monitoring_sync.py` can import it. No production code; verified by being imported in Task 5.

**Files:**
- Create: `tests/support.py`

- [ ] **Step 1: Create the helper**

Create `tests/support.py`:

```python
from __future__ import annotations

from typing import Any

from pygazelle.errors import GazelleNotFoundError


def make_torrent_row(torrent_id: int) -> dict[str, Any]:
    """A minimal dict that validates as a pygazelle Torrent (all required fields)."""
    return {
        "id": torrent_id,
        "media": "CD",
        "format": "FLAC",
        "encoding": "Lossless",
        "scene": False,
        "hasLog": False,
        "hasCue": False,
        "logScore": 0,
        "fileCount": 1,
        "size": 1,
        "seeders": 1,
        "leechers": 0,
        "snatched": 0,
        "time": "2020-01-01 00:00:00",
        "filePath": "x",
    }


def make_user_torrent_row(torrent_id: int, group_id: int, name: str) -> dict[str, Any]:
    """A dict that validates as a UserTorrent."""
    return {"torrentId": torrent_id, "groupId": group_id, "name": name}


class MonitorTransport:
    """Fake transport for monitor tests.

    Parameters
    ----------
    user_id: returned by the ``index`` action as the current user's id.
    pages: ``{type: [[rows_page0], [rows_page1], ...]}`` — each row is a
        ``user_torrents`` item dict (use ``make_user_torrent_row``). Offset is
        mapped to a page index via ``limit``.
    groups: ``{group_id: [torrent_id, ...]}`` — the torrents currently in a group
        (used by ``torrentgroup`` lookups during classification).
    missing_groups: group ids whose ``torrentgroup`` lookup raises NotFound.
    fail_action: optional ``(action, exc)`` — raise ``exc`` whenever ``action`` is
        requested (used to test atomic-commit-on-error).
    """

    def __init__(
        self,
        *,
        user_id: int = 1,
        pages: dict[str, list[list[dict[str, Any]]]] | None = None,
        groups: dict[int, list[int]] | None = None,
        missing_groups: tuple[int, ...] = (),
        fail_action: tuple[str, Exception] | None = None,
    ) -> None:
        self._user_id = user_id
        self._pages = pages or {}
        self._groups = groups or {}
        self._missing = set(missing_groups)
        self._fail_action = fail_action
        self.group_lookups: list[int] = []

    async def request(self, action: str, **params: Any) -> Any:
        if self._fail_action and action == self._fail_action[0]:
            raise self._fail_action[1]
        if action == "index":
            return {"id": self._user_id, "username": "tester"}
        if action == "user_torrents":
            kind = params["type"]
            limit = params.get("limit") or 1
            offset = params.get("offset") or 0
            pages = self._pages.get(kind, [[]])
            idx = offset // limit
            rows = pages[idx] if idx < len(pages) else []
            return {kind: rows, "total": sum(len(p) for p in pages)}
        if action == "torrentgroup":
            gid = params["id"]
            self.group_lookups.append(gid)
            if gid in self._missing:
                raise GazelleNotFoundError(f"group {gid} not found")
            tids = self._groups.get(gid, [])
            return {
                "group": {"id": gid, "name": f"Group {gid}", "year": 2020},
                "torrents": [make_torrent_row(t) for t in tids],
            }
        raise AssertionError(f"unexpected action: {action}")

    async def download(self, torrent_id: int) -> bytes:  # pragma: no cover - unused
        return b""
```

- [ ] **Step 2: Sanity-check the import**

Run: `uv run python -c "from tests.support import MonitorTransport, make_user_torrent_row; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add tests/support.py
git commit -m "test(monitoring): add MonitorTransport fake + row helpers"
```

---

## Task 5: `TorrentMonitor` — baseline, diff, and classification

**Files:**
- Create: `src/pygazelle/monitoring.py`
- Test: `tests/test_monitoring.py`

- [ ] **Step 1: Write the failing tests (baseline + diff + classification)**

Create `tests/test_monitoring.py`:

```python
from pygazelle.client import GazelleClient
from pygazelle.models.monitoring import TorrentChangeEvent
from pygazelle.monitoring import TorrentMonitor
from tests.support import MonitorTransport, make_user_torrent_row


def _client(transport: MonitorTransport) -> GazelleClient:
    return GazelleClient(transport)  # type: ignore[arg-type]


async def test_first_poll_establishes_baseline_returns_empty():
    transport = MonitorTransport(
        pages={
            "uploaded": [[make_user_torrent_row(10, 5, "A")]],
            "snatched": [[make_user_torrent_row(20, 6, "B")]],
        }
    )
    monitor = TorrentMonitor(_client(transport))
    assert await monitor.poll() == []


async def test_no_change_poll_returns_empty():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")]], "snatched": [[]]}
    )
    monitor = TorrentMonitor(_client(transport))
    await monitor.poll()  # baseline
    assert await monitor.poll() == []


async def test_deleted_when_group_gone():
    # Baseline has torrent 10 in group 5; on the next poll it disappears and
    # group 5 no longer exists -> deleted.
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        missing_groups=(5,),
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()  # baseline (page with torrent 10)
    events = await monitor.poll()  # torrent 10 gone
    assert [e.kind for e in events] == ["deleted"]
    assert events[0].torrent_id == 10
    assert events[0].group_id == 5
    assert events[0].name == "A"
    assert events[0].replacement_torrent_id is None


async def test_trumped_when_replacement_present():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        groups={5: [11]},  # group 5 still exists, now contains torrent 11 (not 10)
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()
    events = await monitor.poll()
    assert events[0].kind == "trumped"
    assert events[0].replacement_torrent_id == 11


async def test_deleted_when_group_present_but_empty():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        groups={5: []},  # group exists, our torrent gone, nothing replaced it
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()
    events = await monitor.poll()
    assert events[0].kind == "deleted"


async def test_removed_when_list_and_group_disagree():
    # List says torrent 10 is gone, but the group still lists it -> ambiguous.
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        groups={5: [10]},
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()
    events = await monitor.poll()
    assert events[0].kind == "removed"
    assert events[0].replacement_torrent_id is None


async def test_classification_lookups_bounded_by_removals():
    # 2 watched torrents, only 1 disappears -> exactly 1 group lookup.
    transport = MonitorTransport(
        pages={
            "uploaded": [
                [make_user_torrent_row(10, 5, "A"), make_user_torrent_row(20, 6, "B")],
                [make_user_torrent_row(20, 6, "B")],
            ],
            "snatched": [[]],
        },
        missing_groups=(5,),
    )
    monitor = TorrentMonitor(_client(transport), page_size=2)
    await monitor.poll()
    await monitor.poll()
    assert transport.group_lookups == [5]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_monitoring.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pygazelle.monitoring'`.

- [ ] **Step 3: Implement `TorrentMonitor`**

Create `src/pygazelle/monitoring.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import GazelleNotFoundError
from .models.monitoring import MonitoredTorrent, MonitorSnapshot, TorrentChangeEvent

if TYPE_CHECKING:
    from .client import GazelleClient
    from .resources.user import UserTorrentType

DEFAULT_SOURCES: tuple[str, ...] = ("uploaded", "snatched")


class TorrentMonitor:
    """Watches the current user's torrent lists and reports deletions/trumps.

    Stateless from the caller's view: each ``poll()`` returns the changes since
    the previous snapshot. The monitor runs no loop, timer, or callbacks — the
    caller controls cadence. Build one via ``client.monitor(...)``.
    """

    def __init__(
        self,
        client: GazelleClient,
        *,
        sources: tuple[UserTorrentType, ...] = ("uploaded", "snatched"),
        page_size: int = 50,
    ) -> None:
        self._client = client
        self._sources = tuple(sources)
        self._page_size = page_size
        self._user_id: int | None = None
        self._snapshot: MonitorSnapshot | None = None

    async def poll(self) -> list[TorrentChangeEvent]:
        if self._user_id is None:
            self._user_id = (await self._client.user.me()).id

        current = MonitorSnapshot()
        for source in self._sources:
            current.sources[source] = await self._fetch_source(self._user_id, source)

        if self._snapshot is None:
            self._snapshot = current
            return []

        events: list[TorrentChangeEvent] = []
        for source in self._sources:
            prior = self._snapshot.sources.get(source, {})
            now = current.sources.get(source, {})
            for torrent_id, entry in prior.items():
                if torrent_id not in now:
                    events.append(await self._classify(source, entry))

        # Atomic commit: only advance the snapshot once every fetch + lookup
        # above succeeded. A mid-poll error leaves the prior snapshot intact.
        self._snapshot = current
        return events

    async def _fetch_source(
        self, user_id: int, source: str
    ) -> dict[int, MonitoredTorrent]:
        entries: dict[int, MonitoredTorrent] = {}
        offset = 0
        while True:
            page = await self._client.user.torrents(
                user_id,
                source,  # type: ignore[arg-type]
                limit=self._page_size,
                offset=offset,
            )
            if not page:
                break
            new = 0
            for ut in page:
                if ut.torrent_id not in entries:
                    entries[ut.torrent_id] = MonitoredTorrent(
                        torrent_id=ut.torrent_id, group_id=ut.group_id, name=ut.name
                    )
                    new += 1
            # Stop on a short/last page, or if the tracker ignored offset and
            # returned no new ids (guards against an infinite loop).
            if len(page) < self._page_size or new == 0:
                break
            offset += self._page_size
        return entries

    async def _classify(
        self, source: str, entry: MonitoredTorrent
    ) -> TorrentChangeEvent:
        try:
            group = await self._client.torrents.get_group(entry.group_id)
        except GazelleNotFoundError:
            return self._event("deleted", source, entry, None)

        group_ids = [t.id for t in group.torrents]
        if entry.torrent_id in group_ids:
            # The list says it's gone but the group still lists it — ambiguous.
            return self._event("removed", source, entry, None)
        others = [tid for tid in group_ids if tid != entry.torrent_id]
        if others:
            return self._event("trumped", source, entry, others[0])
        return self._event("deleted", source, entry, None)

    @staticmethod
    def _event(
        kind: str, source: str, entry: MonitoredTorrent, replacement: int | None
    ) -> TorrentChangeEvent:
        return TorrentChangeEvent(
            kind=kind,  # type: ignore[arg-type]
            source=source,
            torrent_id=entry.torrent_id,
            group_id=entry.group_id,
            name=entry.name,
            replacement_torrent_id=replacement,
        )

    def dump_state(self) -> dict[str, object] | None:
        """A json-serializable snapshot, or None before the first poll."""
        if self._snapshot is None:
            return None
        return self._snapshot.model_dump(mode="json")

    def load_state(self, state: dict[str, object]) -> None:
        """Restore a snapshot previously produced by ``dump_state()``."""
        self._snapshot = MonitorSnapshot.model_validate(state)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_monitoring.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/monitoring.py tests/test_monitoring.py
git commit -m "feat(monitoring): add TorrentMonitor with snapshot-diff detection and classification"
```

---

## Task 5b (CONDITIONAL on Task 1 §1.3): targeted deletion recheck

> **Only do this task if the Task 1 spike found that deleted torrents LINGER in `user_torrents`.** If they drop off (or the spike was not run), skip this task entirely — the snapshot diff already detects removals. Implements tasks.md §4.5.

**Files:**
- Modify: `src/pygazelle/monitoring.py`
- Test: `tests/test_monitoring.py`

- [ ] **Step 1: Write the failing test** — a torrent still present in the list but whose `torrents.get(torrent_id)` raises `GazelleNotFoundError` is reported as `deleted`. (Mirror the existing classification tests; add a `get`-by-id branch to `MonitorTransport` that 404s configured torrent ids.)

- [ ] **Step 2–4:** Add a per-source recheck pass in `poll()` that, for torrents still present in the list, issues a bounded `self._client.torrents.get(torrent_id)` only when the spike rules require it; classify a `GazelleNotFoundError` as `deleted`. Run the test; make it pass.

- [ ] **Step 5: Commit** `feat(monitoring): confirm lingering deletions via targeted recheck`.

---

## Task 6: Atomic commit + source restriction

**Files:**
- Modify: `tests/test_monitoring.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_monitoring.py`:

```python
import pytest

from pygazelle.errors import GazelleAPIError


async def test_failed_poll_preserves_prior_snapshot():
    # Baseline succeeds; the second poll fails while fetching the snatched list.
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")]], "snatched": [[]]},
    )
    monitor = TorrentMonitor(_client(transport))
    await monitor.poll()  # baseline OK

    # Make the next user_torrents fetch raise.
    transport._fail_action = ("user_torrents", GazelleAPIError(status_code=500))
    with pytest.raises(GazelleAPIError):
        await monitor.poll()

    # Recover: torrent 10 has since disappeared and its group is gone.
    transport._fail_action = None
    transport._pages = {"uploaded": [[]], "snatched": [[]]}
    transport._missing = {5}
    events = await monitor.poll()
    assert [e.kind for e in events] == ["deleted"]  # change still detected


async def test_source_restriction_watches_only_requested():
    transport = MonitorTransport(
        pages={
            "uploaded": [[make_user_torrent_row(10, 5, "A")]],
            "snatched": [[make_user_torrent_row(20, 6, "B")]],
        }
    )
    monitor = TorrentMonitor(_client(transport), sources=("snatched",))
    await monitor.poll()
    # Snapshot must contain only the snatched source.
    assert set(monitor._snapshot.sources) == {"snatched"}
    assert 20 in monitor._snapshot.sources["snatched"]
```

- [ ] **Step 2: Run tests to verify they fail or pass**

Run: `uv run pytest tests/test_monitoring.py -k "preserves or restriction" -q`
Expected: PASS (the Task 5 implementation already satisfies these — the atomic commit line runs only after all lookups, and `_sources` already gates fetching). If either fails, fix `poll()`/`_fetch_source` accordingly before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/test_monitoring.py
git commit -m "test(monitoring): cover atomic-commit-on-error and source restriction"
```

---

## Task 7: `dump_state` / `load_state` round-trip

**Files:**
- Modify: `tests/test_monitoring.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_monitoring.py`:

```python
import json


async def test_dump_and_load_state_round_trip():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        missing_groups=(5,),
    )
    source = TorrentMonitor(_client(transport), page_size=1)
    await source.poll()  # baseline with torrent 10

    state = source.dump_state()
    assert json.loads(json.dumps(state)) == state  # genuinely json-serializable

    # Restore into a fresh monitor; it treats the restored snapshot as baseline.
    restored = TorrentMonitor(_client(transport), page_size=1)
    restored.load_state(state)
    events = await restored.poll()  # torrent 10 now gone, group 5 missing
    assert [e.kind for e in events] == ["deleted"]


async def test_dump_state_before_first_poll_is_none():
    transport = MonitorTransport(pages={"uploaded": [[]], "snatched": [[]]})
    assert TorrentMonitor(_client(transport)).dump_state() is None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_monitoring.py -k "state" -q`
Expected: PASS (`dump_state`/`load_state` were implemented in Task 5).

- [ ] **Step 3: Commit**

```bash
git add tests/test_monitoring.py
git commit -m "test(monitoring): cover dump_state/load_state json round-trip"
```

---

## Task 8: `client.monitor()` factory

**Files:**
- Modify: `src/pygazelle/client.py`
- Test: `tests/test_monitoring.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_monitoring.py`:

```python
async def test_client_monitor_factory_returns_bound_monitor():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")]], "snatched": [[]]}
    )
    client = _client(transport)
    monitor = client.monitor()
    assert isinstance(monitor, TorrentMonitor)
    # It issues requests through this client's transport.
    assert await monitor.poll() == []


async def test_client_monitor_factory_passes_sources():
    transport = MonitorTransport(pages={"snatched": [[]]})
    monitor = _client(transport).monitor(sources=("snatched",))
    await monitor.poll()
    assert set(monitor._snapshot.sources) == {"snatched"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_monitoring.py -k "factory" -q`
Expected: FAIL — `AttributeError: 'GazelleClient' object has no attribute 'monitor'`.

- [ ] **Step 3: Add the factory**

In `src/pygazelle/client.py`, add the import near the other resource imports (top of file):

```python
from .monitoring import TorrentMonitor
from .resources.user import UserResource, UserTorrentType
```

(`UserResource` is already imported on line 14 — extend that line to also import `UserTorrentType`, and add the `TorrentMonitor` import line.)

Then add this method to `GazelleClient` (e.g. after the `site` property, before `aclose`):

```python
    def monitor(
        self,
        *,
        sources: tuple[UserTorrentType, ...] = ("uploaded", "snatched"),
        page_size: int = 50,
    ) -> TorrentMonitor:
        """Construct a TorrentMonitor bound to this client."""
        return TorrentMonitor(self, sources=sources, page_size=page_size)
```

- [ ] **Step 4: Run tests + full unit suite (import-cycle guard)**

Run: `uv run pytest tests/test_monitoring.py -k "factory" -q && uv run pytest --ignore=tests/integration -q`
Expected: PASS, and no `ImportError`/circular-import failure (confirms `client.py` → `monitoring.py` with the `TYPE_CHECKING` back-reference is acyclic at runtime).

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/client.py tests/test_monitoring.py
git commit -m "feat(client): add monitor() factory for TorrentMonitor"
```

---

## Task 9: Synchronous monitor surface

**Files:**
- Modify: `src/pygazelle/sync.py`
- Test: `tests/test_monitoring_sync.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_monitoring_sync.py`:

```python
from pygazelle.client import GazelleClient
from pygazelle.sync import GazelleSyncClient
from tests.support import MonitorTransport, make_user_torrent_row


def test_sync_monitor_poll_returns_without_await():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        missing_groups=(5,),
    )
    sync_client = GazelleSyncClient(GazelleClient(transport))  # type: ignore[arg-type]
    try:
        monitor = sync_client.monitor(page_size=1)
        assert monitor.poll() == []  # baseline, no await
        events = monitor.poll()  # torrent 10 gone
        assert [e.kind for e in events] == ["deleted"]
        # Sync (non-coroutine) methods pass through unchanged.
        assert monitor.dump_state() is not None
    finally:
        sync_client.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_monitoring_sync.py -q`
Expected: FAIL — `AttributeError: 'GazelleSyncClient' object has no attribute 'monitor'`.

- [ ] **Step 3: Add the sync factory**

In `src/pygazelle/sync.py`, add `UserTorrentType` to the imports:

```python
from .resources.user import UserTorrentType
```

Then add this method to `GazelleSyncClient` (after the `site` property, before `close`):

```python
    def monitor(
        self,
        *,
        sources: tuple[UserTorrentType, ...] = ("uploaded", "snatched"),
        page_size: int = 50,
    ) -> _SyncProxy:
        """A synchronous TorrentMonitor: async ``poll()`` runs on the background
        loop; sync methods (``dump_state``/``load_state``) pass through."""
        async_monitor = self._async.monitor(sources=sources, page_size=page_size)
        return _SyncProxy(async_monitor, self._bg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_monitoring_sync.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/sync.py tests/test_monitoring_sync.py
git commit -m "feat(sync): expose monitor() on the synchronous client surface"
```

---

## Task 10: Top-level public exports

**Files:**
- Modify: `src/pygazelle/__init__.py`
- Test: `tests/test_monitoring.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_monitoring.py`:

```python
def test_public_exports():
    import pygazelle

    assert pygazelle.TorrentMonitor is TorrentMonitor
    assert pygazelle.TorrentChangeEvent is TorrentChangeEvent
    assert "TorrentMonitor" in pygazelle.__all__
    assert "TorrentChangeEvent" in pygazelle.__all__
```

(`TorrentChangeEvent` is already imported at the top of this test module via `from pygazelle.models.monitoring import TorrentChangeEvent`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_monitoring.py -k exports -q`
Expected: FAIL — `AttributeError: module 'pygazelle' has no attribute 'TorrentMonitor'`.

- [ ] **Step 3: Add the exports**

In `src/pygazelle/__init__.py`, add imports after the existing ones:

```python
from .models.monitoring import TorrentChangeEvent
from .monitoring import TorrentMonitor
```

Add to `__all__`:

```python
    "TorrentMonitor",
    "TorrentChangeEvent",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_monitoring.py -k exports -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pygazelle/__init__.py tests/test_monitoring.py
git commit -m "feat(monitoring): export TorrentMonitor and TorrentChangeEvent from pygazelle"
```

---

## Task 11: Opt-in live integration test

**Files:**
- Create: `tests/integration/test_user_torrents_live.py`

- [ ] **Step 1: Write the integration test (skips without creds)**

Look at an existing file in `tests/integration/` first to match the credential-loading + skip pattern. Then create `tests/integration/test_user_torrents_live.py`:

```python
import os

import pytest

from pygazelle.client import OrpheusClient

ORPHEUS_API_KEY = os.getenv("ORPHEUS_API_KEY")


@pytest.mark.skipif(not ORPHEUS_API_KEY, reason="ORPHEUS_API_KEY not set")
async def test_user_torrents_single_live_read():
    # Read-only, single request, no retries (live-API care: never loop on bans).
    client = OrpheusClient(api_key=ORPHEUS_API_KEY, max_retries=0)
    try:
        me = await client.user.me()
        results = await client.user.torrents(me.id, "uploaded", limit=5)
        assert isinstance(results, list)
    finally:
        await client.aclose()
```

> If `tests/integration/` uses a shared fixture/conftest for the client or credentials, follow that instead of constructing the client inline. Confirm `max_retries` is the correct `TransportOptions` key by checking `src/pygazelle/transport.py`; adjust if the kwarg differs.

- [ ] **Step 2: Verify it skips cleanly without creds**

Run: `uv run pytest tests/integration/test_user_torrents_live.py -q`
Expected: `1 skipped` (no creds) — never a failure.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_user_torrents_live.py
git commit -m "test(integration): opt-in live user_torrents read"
```

---

## Task 12: Docs + full quality gate

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a monitoring example to the README**

Find the usage/examples section in `README.md` and add:

````markdown
### Monitoring your uploads & snatches

```python
from pygazelle import OrpheusClient

async with OrpheusClient(api_key="...") as client:
    monitor = client.monitor()           # watches uploaded + snatched by default
    await monitor.poll()                  # first call establishes the baseline -> []

    # ... later (you control the cadence) ...
    for event in await monitor.poll():
        print(event.kind, event.source, event.torrent_id, event.name)
        if event.kind == "trumped":
            print("replaced by", event.replacement_torrent_id)

    # Persist the baseline across restarts (storage is yours):
    state = monitor.dump_state()          # json-serializable
    # monitor.load_state(state)
```
````

- [ ] **Step 2: Run the full quality gate** (tasks.md §6.2)

Run each; all must be clean:

```bash
uv run pytest --ignore=tests/integration
uv run ruff check .
uv run ruff format
uv run basedpyright
uv run codespell
```

Expected: tests pass (new monitoring tests included, integration/model skips OK); ruff 0 errors; basedpyright 0 errors / 0 warnings; codespell clean.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add TorrentMonitor usage example"
```

---

## Self-Review (completed during planning)

**Spec coverage** (delta `torrent-monitoring/spec.md` + `gazelle-client/spec.md`):

| Requirement | Task |
|---|---|
| Auto-discovered watch list (default uploaded+snatched; current user resolved via `me()`) | Task 5 (`poll`, `_fetch_source`, `_user_id`) |
| Source restriction | Task 6 |
| Stateless `poll()`, no loop/callbacks | Task 5 |
| First poll → baseline → `[]`; no-change → `[]`; change reported | Task 5 |
| Deletion / trump / removal classification (+ replacement id) | Task 5 |
| Rate-limit-safe detection; lookups bounded by removals | Task 5 (`test_classification_lookups_bounded_by_removals`) |
| Atomic snapshot commit | Task 6 |
| Serializable monitor state | Task 7 |
| Synchronous monitor surface | Task 9 |
| Monitor factory (gazelle-client delta) | Task 8 |
| Top-level exports (tasks.md §5.5) | Task 10 |
| Fixture spike / assumption B (tasks.md §1) | Tasks 1, 5b |
| Endpoint confirmation (tasks.md §2.6) | Task 2 |
| Integration test (§6.1), quality gate (§6.2), docs (§6.3) | Tasks 11, 12 |

**Placeholder scan:** No TBD/"handle edge cases"/"similar to" — every code step has complete code. Task 5b is intentionally conditional (gated on the spike) and describes its test/impl shape because its exact branch depends on spike data not yet available; it is skipped by default.

**Type consistency:** `TorrentMonitor(client, *, sources, page_size)`; `poll() -> list[TorrentChangeEvent]`; `dump_state() -> dict|None`; `load_state(dict)`; `MonitoredTorrent(torrent_id, group_id, name)`; `MonitorSnapshot(sources: dict[str, dict[int, MonitoredTorrent]])`; `TorrentChangeEvent(kind, source, torrent_id, group_id, name, replacement_torrent_id)` — consistent across all tasks and matching the shipped `UserTorrent`/`TorrentGroup`/`Torrent` field names.
