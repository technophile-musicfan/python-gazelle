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
