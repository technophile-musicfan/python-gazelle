from typing import Any

from pydantic import Field

from .base import GazelleModel


class ArtistTag(GazelleModel):
    name: str
    count: int


class ArtistStatistics(GazelleModel):
    """The `statistics` block of an action=artist response."""

    num_groups: int | None = None
    num_torrents: int | None = None
    num_seeders: int | None = None
    num_leechers: int | None = None
    num_snatches: int | None = None
    num_requests: int | None = None


class ArtistSimilar(GazelleModel):
    """An entry of the action=artist `similarArtists` block.

    Distinct from :class:`SimilarArtist` (action=similar_artists): the profile
    block keys the artist as ``artistId`` and adds a ``similarId`` edge id.
    """

    artist_id: int | None = None
    name: str | None = None
    score: int | None = None
    similar_id: int | None = None


class DiscographyArtist(GazelleModel):
    """An artist credit inside a discography group (action=artist)."""

    id: int | None = None
    name: str | None = None
    aliasid: int | None = None


class DiscographyTorrent(GazelleModel):
    """A torrent inside a discography group (the singular ``torrent`` entries)."""

    id: int | None = None
    group_id: int | None = None
    media: str | None = None
    format: str | None = None
    encoding: str | None = None
    remaster_year: int | None = None
    remaster_title: str | None = None
    remaster_record_label: str | None = None
    remaster_catalogue_number: str | None = None
    scene: bool | None = None
    has_log: bool | None = None
    has_cue: bool | None = None
    log_score: int | None = None
    file_count: int | None = None
    free_torrent: bool | str | None = None
    size: int | None = None
    leechers: int | None = None
    seeders: int | None = None
    snatched: int | None = None
    time: str | None = None
    has_file: bool | None = None


class ArtistTorrentGroup(GazelleModel):
    """A discography group from action=artist's ``torrentgroup`` list.

    Note the shape differs from action=torrentgroup (``groupId``/``groupName``,
    ``tags`` as a ``{tagId: name}`` map, a singular ``torrent`` key), so this is
    a dedicated model rather than a reuse of :class:`~.torrents.TorrentGroup`.
    """

    group_id: int | None = None
    group_name: str | None = None
    group_year: int | None = None
    # API key is "groupCategoryID" (capital ID) — to_camel would emit "...Id".
    group_category_id: int | None = Field(default=None, alias="groupCategoryID")
    tags: dict[str, str] | list[str] = Field(default_factory=dict)
    release_type: int | None = None
    wiki_image: str | None = None
    group_vanity_house: bool | None = None
    has_bookmarked: bool | None = None
    artists: list[DiscographyArtist] = []
    extended_artists: dict[str, Any] | None = None
    # The API uses a singular "torrent" key for the edition list.
    torrents: list[DiscographyTorrent] = Field(default_factory=list, alias="torrent")


class Artist(GazelleModel):
    id: int
    name: str
    body: str = ""
    image: str = ""
    # RED returns a list of tag names; Orpheus returns objects with a usage count.
    tags: list[ArtistTag] | list[str] = []
    # Enrichment from action=artist; Optional/tolerant for trackers/responses
    # that omit them (e.g. light artist references).
    vanity_house: bool | None = None
    body_bbcode: str | None = None
    statistics: ArtistStatistics | None = None
    similar_artists: list[ArtistSimilar] = []
    # The artist's discography is keyed "torrentgroup" (singular) in the response.
    discography: list[ArtistTorrentGroup] = Field(default_factory=list, alias="torrentgroup")


class ArtistResult(GazelleModel):
    id: int
    name: str


class SimilarArtist(GazelleModel):
    id: int
    name: str
    score: int | None = None  # relatedness weight; absent on some responses
