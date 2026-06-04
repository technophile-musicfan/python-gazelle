from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import GazelleNotFoundError
from .models.monitoring import MonitoredTorrent, MonitorSnapshot, TorrentChangeEvent

if TYPE_CHECKING:
    from .client import GazelleClient
    from .resources.user import UserTorrentType

from .models.monitoring import ChangeKind


class TorrentMonitor:
    """Watches the current user's torrent lists and reports deletions/trumps.

    Stateless from the caller's view: each ``poll()`` returns the changes since
    the previous snapshot. The monitor runs no loop, timer, or callbacks — the
    caller controls cadence. Build one via ``client.monitor(...)``.
    """

    _client: GazelleClient
    _sources: tuple[UserTorrentType, ...]
    _page_size: int

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
        self, user_id: int, source: UserTorrentType
    ) -> dict[int, MonitoredTorrent]:
        entries: dict[int, MonitoredTorrent] = {}
        offset = 0
        while True:
            page = await self._client.user.torrents(
                user_id,
                source,
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

    async def _classify(self, source: str, entry: MonitoredTorrent) -> TorrentChangeEvent:
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
        kind: ChangeKind, source: str, entry: MonitoredTorrent, replacement: int | None
    ) -> TorrentChangeEvent:
        return TorrentChangeEvent(
            kind=kind,
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
