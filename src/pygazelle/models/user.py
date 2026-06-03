from pydantic import Field

from .base import GazelleModel


class UserStats(GazelleModel):
    uploaded: int
    downloaded: int
    ratio: float
    # Orpheus omits requiredRatio from its index response; RED includes it.
    required_ratio: float | None = None


class User(GazelleModel):
    id: int
    username: str
    userstats: UserStats | None = None


class UserProfileStats(GazelleModel):
    """The `stats` block of an action=user profile response."""

    joined_date: str | None = None
    last_access: str | None = None
    uploaded: int | None = None
    downloaded: int | None = None
    ratio: float | None = None
    required_ratio: float | None = None


class UserCommunity(GazelleModel):
    """The `community` block of an action=user profile response (subset)."""

    uploaded: int | None = None  # number of torrents uploaded
    groups: int | None = None
    seeding: int | None = None
    leeching: int | None = None
    snatched: int | None = None
    posts: int | None = None


class UserProfile(GazelleModel):
    """A public user profile (action=user). Distinct from the index `User`:
    the API omits the user id (it's the request param) and nests stats under
    `stats`/`community` rather than `userstats`. Private blocks (ranks,
    personal/passkey) are intentionally ignored.
    """

    id: int  # injected by the resource from the request param; the API omits it
    username: str
    avatar: str | None = None
    is_friend: bool | None = None
    profile_text: str | None = None
    stats: UserProfileStats | None = None
    community: UserCommunity | None = None


class UserSearchResult(GazelleModel):
    user_id: int
    username: str
    donor: bool | None = None
    warned: bool | None = None
    enabled: bool | None = None
    # `class` is a Python keyword, so it needs an explicit alias.
    user_class: str | None = Field(default=None, alias="class")


class UserTorrent(GazelleModel):
    """An item from action=user_torrents (uploaded/seeding/snatched/...)."""

    group_id: int
    torrent_id: int
    name: str
    torrent_size: int | None = None
    artist_id: int | None = None
    artist_name: str | None = None
