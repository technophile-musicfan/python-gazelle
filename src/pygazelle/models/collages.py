from .base import GazelleModel


class Collage(GazelleModel):
    id: int
    name: str
    description: str = ""
    tags: list[str] = []
    num_torrents: int = 0
