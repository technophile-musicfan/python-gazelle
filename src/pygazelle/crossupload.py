from __future__ import annotations

import logging
from dataclasses import dataclass, field
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


@dataclass
class MappedForm:
    fields: dict[str, Any] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# VERIFY: Orpheus<->Redacted release-type ids. Keyed by source release_type int,
# valued per target tracker. Missing entries -> unmapped (safe).
RELEASE_TYPE_MAP: dict[TrackerKind, dict[int, int]] = {
    "redacted": {
        1: 1,
        3: 3,
        5: 5,
        6: 6,
        7: 7,
        9: 9,
        11: 11,
        13: 13,
        14: 14,
        15: 15,
        16: 16,
        17: 17,
        18: 18,
        19: 19,
        21: 21,
    },
    "orpheus": {
        1: 1,
        3: 3,
        5: 5,
        6: 6,
        7: 7,
        9: 9,
        11: 11,
        13: 13,
        14: 14,
        15: 15,
        16: 16,
        17: 17,
        18: 18,
        19: 19,
        21: 21,
    },
}

# VERIFY: the target upload form field names + required set per tracker.
REQUIRED_FIELDS: dict[TrackerKind, tuple[str, ...]] = {
    "redacted": ("artists", "title", "year", "release_type", "format", "bitrate", "media"),
    "orpheus": ("artists", "title", "year", "release_type", "format", "bitrate", "media"),
}


def map_metadata(source: Torrent, target: TrackerKind) -> MappedForm:
    """Best-effort map of a source release's metadata to the target upload schema.

    Confident fields go to ``fields``; anything unmappable/uncertain is recorded in
    ``unmapped`` + ``warnings`` and never guessed.
    """
    out = MappedForm()
    group = source.group
    if group is not None:
        out.fields["title"] = group.name
        out.fields["year"] = group.year
        out.fields["artists"] = [a.name for a in group.artists]
        if group.tags:
            out.fields["tags"] = list(group.tags)
            out.warnings.append("tags carried over verbatim; review against the target's tag rules")
        rt = group.release_type
        mapped_rt = RELEASE_TYPE_MAP.get(target, {}).get(rt) if rt is not None else None
        if mapped_rt is not None:
            out.fields["release_type"] = mapped_rt
        else:
            out.unmapped.append("release_type")
            out.warnings.append(f"release type {rt} has no {target} equivalent; set it manually")
    out.fields["format"] = source.format
    out.fields["bitrate"] = source.encoding  # Gazelle 'bitrate' carries the encoding value
    out.fields["media"] = source.media
    return out
