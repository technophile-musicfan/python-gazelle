import html
from typing import Any, cast

from pydantic import AliasChoices, Field, model_validator

from .base import GazelleModel


class TorrentFile(GazelleModel):
    path: str
    size: int


def _parse_file_list(raw: str) -> list[TorrentFile]:
    """Parse a Gazelle ``fileList`` ("name{{{size}}}|||name{{{size}}}") string.

    Names are HTML-entity-encoded in the API (e.g. ``&rsquo;``) and are decoded
    here so they line up with file names reported elsewhere (e.g. qBittorrent).
    """
    files: list[TorrentFile] = []
    for entry in raw.split("|||"):
        entry = entry.strip()
        if not entry:
            continue
        name, _, rest = entry.partition("{{{")
        size = int(rest.rstrip("}").strip())
        files.append(TorrentFile(path=html.unescape(name), size=size))
    return files


class TorrentArtist(GazelleModel):
    id: int
    name: str


class CollageRef(GazelleModel):
    """A collage a torrent group belongs to (id/name/count only).

    Lighter than :class:`~.collages.Collage` (no contents); defined here rather
    than reusing Collage to avoid a circular import (``collages`` imports
    :class:`TorrentGroup`).
    """

    id: int
    name: str | None = None
    num_torrents: int | None = None


class TorrentGroup(GazelleModel):
    id: int
    name: str
    year: int
    tags: list[str] = []
    artists: list[TorrentArtist] = []
    # Richer fields returned by action=torrentgroup (and present on the embedded
    # group). Optional/tolerant because the two trackers diverge on which they send.
    category_id: int | None = None
    category_name: str | None = None
    release_type: int | None = None
    # Human-readable release type ("Album"/"EP"/...); Orpheus-only (RED omits).
    release_type_name: str | None = None
    record_label: str | None = None  # RED top-level; Orpheus omits (per-edition only)
    catalogue_number: str | None = None
    vanity_house: bool | None = None
    wiki_image: str | None = None
    wiki_body: str | None = None
    # BBcode source of the wiki body: Orpheus sends "wikiBBcode", RED sends "bbBody".
    wiki_bbcode: str | None = Field(
        default=None, validation_alias=AliasChoices("wikiBBcode", "bbBody")
    )
    proxy_image: str | None = None  # proxied cover URL; Orpheus-only
    is_bookmarked: bool | None = None
    time: str | None = None
    # Collage memberships (RED group block; Orpheus omits).
    collages: list[CollageRef] = []
    personal_collages: list[CollageRef] = []
    # Populated by TorrentResource.get_group(); empty when this group is embedded
    # in a single Torrent (action=torrent).
    torrents: list["Torrent"] = []

    @model_validator(mode="before")
    @classmethod
    def _artists_from_music_info(cls, data: Any) -> Any:
        # The API nests artists under musicInfo.artists with no top-level "artists"
        # key; surface them on `artists` unless explicitly provided.
        if not isinstance(data, dict):
            return data
        values = cast("dict[str, Any]", data)
        # Presence, not truthiness: respect an explicit "artists": [] from the caller.
        if "artists" in values:
            return values
        music_info = values.get("musicInfo")
        if isinstance(music_info, dict):
            artists = cast("dict[str, Any]", music_info).get("artists")
            if artists:
                return {**values, "artists": artists}
        return values


class Torrent(GazelleModel):
    id: int
    # Orpheus omits infoHash and remastered; RED includes them.
    info_hash: str | None = None
    media: str
    format: str
    encoding: str
    remastered: bool | None = None
    scene: bool
    has_log: bool
    has_cue: bool
    log_score: int
    file_count: int
    size: int
    seeders: int
    leechers: int
    snatched: int
    # RED returns a bool; Orpheus returns a freeleech-state string enum (e.g. "Normal").
    free_torrent: bool | str | None = None
    time: str
    file_path: str
    user_id: int
    username: str
    group: TorrentGroup | None = None
    file_list: str | None = None  # raw "name{{{size}}}|||..." ("fileList")
    trumpable: bool | None = None
    trumpable_reasons: list[str] = []
    # Edition/remaster info — what distinguishes one release of a group from another.
    remaster_year: int | None = None
    remaster_title: str | None = None
    remaster_record_label: str | None = None
    remaster_catalogue_number: str | None = None
    description: str | None = None
    # Log detail; logChecksum/logCount are Orpheus-only (RED omits them).
    log_checksum: bool | None = None
    log_count: int | None = None
    rip_log_ids: list[int] = []
    free_reason: str | None = None  # Orpheus-only freeleech-state reason
    reported: bool | None = None

    @property
    def files(self) -> list[TorrentFile]:
        return _parse_file_list(self.file_list) if self.file_list else []


class BrowseTorrent(GazelleModel):
    torrent_id: int  # "torrentId"
    size: int
    file_count: int  # "fileCount"
    format: str
    encoding: str
    media: str
    edition_id: int | None = None
    artists: list[TorrentArtist] = []
    remaster_year: int | None = None
    remaster_title: str | None = None
    remaster_record_label: str | None = None
    remaster_catalogue_number: str | None = None
    has_log: bool | None = None
    log_score: int | None = None
    has_cue: bool | None = None
    scene: bool | None = None
    vanity_house: bool | None = None
    time: str | None = None
    seeders: int | None = None
    leechers: int | None = None
    snatches: int | None = None
    is_freeleech: bool | None = None
    is_neutral_leech: bool | None = None
    is_personal_freeleech: bool | None = None
    can_use_token: bool | None = None
    has_snatched: bool | None = None


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
    torrents: list[BrowseTorrent] = []
    cover: str | None = None  # cover image URL
    bookmarked: bool | None = None
    vanity_house: bool | None = None
    # The browse group row reports release type as a string ("Album"/"Remix"),
    # unlike TorrentGroup.release_type which is an int code.
    release_type: str | None = None
    # Datetime string on Orpheus, epoch-seconds string on RED — kept raw.
    group_time: str | None = None


# TorrentGroup.torrents forward-references Torrent (defined after it); resolve now.
TorrentGroup.model_rebuild()
