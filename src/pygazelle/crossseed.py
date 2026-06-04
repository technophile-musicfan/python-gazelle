from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .errors import (
    GazelleNotFoundError,  # noqa: F401  # pyright: ignore[reportUnusedImport]  # used by later cross-seed functions
)
from .models.torrents import Torrent

if TYPE_CHECKING:
    from .client import (
        GazelleClient,  # noqa: F401  # pyright: ignore[reportUnusedImport]  # used by later cross-seed functions
    )

logger = logging.getLogger("pygazelle.crossseed")


@dataclass(frozen=True)
class CrossSeedResult:
    """A confirmed cross-seed match plus the target tracker's .torrent bytes."""

    match: Torrent
    torrent_file: bytes
    source_torrent_id: int
    target_torrent_id: int
    confidence: Literal["exact"] = "exact"
