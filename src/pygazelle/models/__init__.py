from .artists import Artist, ArtistResult, ArtistTag, SimilarArtist
from .collages import Collage
from .inbox import Message
from .notifications import Notification
from .requests import Request, RequestResult
from .torrents import BrowseTorrent, Torrent, TorrentFile, TorrentGroup, TorrentResult
from .user import User, UserStats

__all__ = [
    "Artist",
    "ArtistResult",
    "ArtistTag",
    "SimilarArtist",
    "Collage",
    "Message",
    "Notification",
    "Request",
    "RequestResult",
    "BrowseTorrent",
    "Torrent",
    "TorrentFile",
    "TorrentGroup",
    "TorrentResult",
    "User",
    "UserStats",
]
