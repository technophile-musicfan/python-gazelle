from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .client import (
        GazelleClient,  # noqa: F401  # used by later cross-upload functions  # pyright: ignore[reportUnusedImport]
    )

from .crossseed import (
    find_candidates,  # noqa: F401  # used by later cross-upload functions  # pyright: ignore[reportUnusedImport]
    verify_match,  # noqa: F401  # used by later cross-upload functions  # pyright: ignore[reportUnusedImport]
)
from .errors import (
    GazelleError,  # noqa: F401  # used by later cross-upload functions  # pyright: ignore[reportUnusedImport]
)
from .models.torrents import (
    Torrent,  # noqa: F401  # used by later cross-upload functions  # pyright: ignore[reportUnusedImport]
)

logger = logging.getLogger("pygazelle.crossupload")

TrackerKind = Literal["orpheus", "redacted"]
DuplicateKind = Literal["exact", "possible"]


@dataclass(frozen=True)
class DuplicateMatch:
    torrent_id: int
    group_id: int
    kind: DuplicateKind
    name: str


@dataclass
class UploadDraft:
    """Mutable: the caller fills `form` for any `unmapped` fields before submit."""

    form: dict[str, Any]
    unmapped: list[str]
    warnings: list[str]
    duplicates: list[DuplicateMatch]
    torrent_file: bytes
    source_torrent_id: int
    target_tracker: TrackerKind


@dataclass(frozen=True)
class UploadResult:
    torrent_id: int
    group_id: int
    url: str
