from .base import GazelleModel


class BookmarkedTorrent(GazelleModel):
    """A torrent edition within a bookmarked group (action=bookmarks&type=torrents)."""

    id: int
    group_id: int
    media: str | None = None
    format: str | None = None
    encoding: str | None = None
    size: int | None = None
    seeders: int | None = None
    leechers: int | None = None
    snatched: int | None = None
    has_log: bool | None = None
    has_cue: bool | None = None
    log_score: int | None = None
    scene: bool | None = None
    remastered: bool | None = None
    remaster_year: int | None = None
    # RED returns a bool; Orpheus may return a freeleech-state string.
    free_torrent: bool | str | None = None
    time: str | None = None


class BookmarkedTorrentGroup(GazelleModel):
    """A bookmarked release group (action=bookmarks&type=torrents)."""

    id: int
    name: str
    year: int | None = None
    record_label: str | None = None
    catalogue_number: str | None = None
    tag_list: str | None = None  # space-separated tags, as the API returns them
    release_type: str | None = None
    vanity_house: bool | None = None
    image: str | None = None
    torrents: list[BookmarkedTorrent] = []


class BookmarkedArtist(GazelleModel):
    """A bookmarked artist (action=bookmarks&type=artists)."""

    artist_id: int
    artist_name: str
