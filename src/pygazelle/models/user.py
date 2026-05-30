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
