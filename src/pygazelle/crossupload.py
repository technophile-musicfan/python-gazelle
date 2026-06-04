from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .client import GazelleClient

from .crossseed import find_candidates, verify_match
from .models.torrents import Torrent

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


async def duplicate_check(source: Torrent, target_client: GazelleClient) -> list[DuplicateMatch]:
    """Search the target for releases matching the source; classify each as an
    exact duplicate (file-list match) or a possible duplicate (same group/metadata)."""
    candidates = await find_candidates(source, target_client)
    matches: list[DuplicateMatch] = []
    for cand in candidates:
        kind: DuplicateKind = "exact" if verify_match(source, cand) else "possible"
        group_id = cand.group.id if cand.group else 0
        name = cand.group.name if cand.group else ""
        matches.append(DuplicateMatch(torrent_id=cand.id, group_id=group_id, kind=kind, name=name))
    return matches


def _missing_required(draft: UploadDraft) -> list[str]:
    required = REQUIRED_FIELDS.get(draft.target_tracker, ())
    return [f for f in required if f not in draft.form or draft.form[f] in (None, "", [])]


async def submit_upload(
    target_client: GazelleClient,
    draft: UploadDraft,
    *,
    allow_duplicate: bool = False,
) -> UploadResult:
    """The live write: validate the draft, gate on exact duplicates, then POST
    action=upload. Refuses (no write) on missing required fields or an unallowed
    exact duplicate."""
    missing = _missing_required(draft)
    if missing:
        raise ValueError(f"cannot submit: missing required field(s): {', '.join(missing)}")
    if not allow_duplicate and any(d.kind == "exact" for d in draft.duplicates):
        raise ValueError(
            "an exact duplicate exists on the target; pass allow_duplicate=True to override"
        )
    files = [
        ("file_input", ("upload.torrent", draft.torrent_file))
    ]  # VERIFY upload file field name
    data = await target_client._transport.request_write(  # pyright: ignore[reportPrivateUsage]
        "upload", data=dict(draft.form), files=files
    )
    # VERIFY response keys for the new torrent/group id.
    torrent_id = int(data.get("torrentid") or data.get("torrentId") or 0)
    group_id = int(data.get("groupid") or data.get("groupId") or 0)
    return UploadResult(
        torrent_id=torrent_id,
        group_id=group_id,
        url=f"torrents.php?id={group_id}&torrentid={torrent_id}",
    )
