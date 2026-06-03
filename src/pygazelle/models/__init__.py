from .artists import (
    Artist,
    ArtistResult,
    ArtistSimilar,
    ArtistStatistics,
    ArtistTag,
    ArtistTorrentGroup,
    DiscographyArtist,
    DiscographyTorrent,
    SimilarArtist,
)
from .bookmarks import BookmarkedArtist, BookmarkedTorrent, BookmarkedTorrentGroup
from .collages import Collage
from .inbox import Message
from .notifications import Notification
from .requests import Request, RequestResult
from .site import Announcement, Announcements, BlogPost, Top10Category
from .subscriptions import ForumSubscription
from .torrents import BrowseTorrent, Torrent, TorrentFile, TorrentGroup, TorrentResult
from .user import (
    User,
    UserCommunity,
    UserProfile,
    UserProfileStats,
    UserSearchResult,
    UserStats,
    UserTorrent,
)

__all__ = [
    "Artist",
    "ArtistResult",
    "ArtistTag",
    "ArtistStatistics",
    "ArtistSimilar",
    "ArtistTorrentGroup",
    "DiscographyArtist",
    "DiscographyTorrent",
    "SimilarArtist",
    "BookmarkedTorrent",
    "BookmarkedTorrentGroup",
    "BookmarkedArtist",
    "ForumSubscription",
    "Top10Category",
    "Announcement",
    "BlogPost",
    "Announcements",
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
    "UserProfile",
    "UserProfileStats",
    "UserCommunity",
    "UserSearchResult",
    "UserTorrent",
]
