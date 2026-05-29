from .base import GazelleModel


class UserStats(GazelleModel):
    uploaded: int
    downloaded: int
    ratio: float
    required_ratio: float


class User(GazelleModel):
    id: int
    username: str
    userstats: UserStats | None = None
