from .base import GazelleModel


class TagAddition(GazelleModel):
    """Result of action=add_tag."""

    added: list[str] = []
    rejected: list[str] = []


class LogSummary(GazelleModel):
    """One log's checker summary inside an action=add_log response."""

    score: int | None = None
    checksum: bool | str | None = None
    ripper: str | None = None
    ripper_version: str | None = None
    language: str | None = None
    details: list[str] = []


class LogAddition(GazelleModel):
    """Result of action=add_log."""

    torrent_id: int | None = None
    score: int | None = None
    checksum: bool | str | None = None
    logchecker_version: str | None = None
    log_summaries: list[LogSummary] = []


class RequestFill(GazelleModel):
    """Result of action=request_fill."""

    request_id: int | None = None
    torrent_id: int | None = None
    filler_id: int | None = None
    filler_name: str | None = None
    bounty: int | None = None
