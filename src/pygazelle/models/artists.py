from .base import GazelleModel


class ArtistTag(GazelleModel):
    name: str
    count: int


class Artist(GazelleModel):
    id: int
    name: str
    body: str = ""
    image: str = ""
    # RED returns a list of tag names; Orpheus returns objects with a usage count.
    tags: list[ArtistTag] | list[str] = []


class ArtistResult(GazelleModel):
    id: int
    name: str


class SimilarArtist(GazelleModel):
    id: int
    name: str
    score: int | None = None  # relatedness weight; absent on some responses
