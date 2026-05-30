from .base import GazelleModel


class Artist(GazelleModel):
    id: int
    name: str
    body: str = ""
    image: str = ""
    tags: list[str] = []


class ArtistResult(GazelleModel):
    id: int
    name: str
