from pydantic import Field

from .base import GazelleModel
from .torrents import TorrentGroup


class Collage(GazelleModel):
    id: int
    name: str
    description: str = ""
    tags: list[str] = []
    num_torrents: int = 0
    # action=collage returns the contained groups under "torrentgroups" (all
    # lowercase, so to_camel's "torrentGroups" won't match — alias explicitly).
    # Each entry is shaped like action=torrentgroup, so reuse TorrentGroup.
    torrent_groups: list[TorrentGroup] = Field(default_factory=list, alias="torrentgroups")
