from .base import GazelleModel


class Request(GazelleModel):
    id: int
    title: str
    year: int
    artists: list[str] = []
    tags: list[str] = []
    description: str = ""


class RequestResult(GazelleModel):
    request_id: int
    title: str
    year: int
    artists: list[str] = []
