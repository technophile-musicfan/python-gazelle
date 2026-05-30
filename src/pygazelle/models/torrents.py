from .base import GazelleModel


class TorrentArtist(GazelleModel):
    id: int
    name: str


class TorrentGroup(GazelleModel):
    id: int
    name: str
    year: int
    tags: list[str] = []
    artists: list[TorrentArtist] = []


class Torrent(GazelleModel):
    id: int
    info_hash: str
    media: str
    format: str
    encoding: str
    remastered: bool
    scene: bool
    has_log: bool
    has_cue: bool
    log_score: int
    file_count: int
    size: int
    seeders: int
    leechers: int
    snatched: int
    free_torrent: bool
    time: str
    file_path: str
    user_id: int
    username: str
    group: TorrentGroup | None = None


class TorrentResult(GazelleModel):
    group_id: int
    group_name: str
    artist: str
    tags: list[str] = []
    group_year: int
    max_size: int
    total_seeders: int
    total_leechers: int
    total_snatched: int
