from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .errors import GazelleNotFoundError
from .models.torrents import Torrent

if TYPE_CHECKING:
    from .client import GazelleClient

logger = logging.getLogger("pygazelle.crossseed")


@dataclass(frozen=True)
class CrossSeedResult:
    """A confirmed cross-seed match plus the target tracker's .torrent bytes."""

    match: Torrent
    torrent_file: bytes
    source_torrent_id: int
    target_torrent_id: int
    confidence: Literal["exact"] = "exact"


def verify_match(source: Torrent, candidate: Torrent) -> bool:
    """Strict cross-seed match: identical top-level folder and identical sorted
    (path, size) file list. Empty file lists never match.
    """
    if source.file_path != candidate.file_path:
        return False
    source_files = sorted((f.path, f.size) for f in source.files)
    if not source_files:
        return False
    candidate_files = sorted((f.path, f.size) for f in candidate.files)
    return source_files == candidate_files


DEFAULT_MAX_DEEP_CHECKS = 5


async def find_candidates(
    source: Torrent,
    target_client: GazelleClient,
    *,
    max_deep_checks: int = DEFAULT_MAX_DEEP_CHECKS,
) -> list[Torrent]:
    """Search the target tracker by the source's artist/album, cheaply pre-filter
    candidates on format/encoding/media/size/file_count, then fetch the full
    file list for each survivor (bounded by ``max_deep_checks``).
    """
    artist = source.group.artists[0].name if source.group and source.group.artists else None
    album = source.group.name if source.group else None

    results = []
    if artist:
        params: dict[str, str | int] = {"artistname": artist}
        if album:
            params["groupname"] = album
        results = await target_client.torrents.search("", **params)
    if not results and album:
        results = await target_client.torrents.search("", groupname=album)

    candidate_ids: list[int] = []
    for group in results:
        for row in group.torrents:
            if (
                row.format == source.format
                and row.encoding == source.encoding
                and row.media == source.media
                and row.size == source.size
                and row.file_count == source.file_count
            ):
                candidate_ids.append(row.torrent_id)

    if len(candidate_ids) > max_deep_checks:
        logger.warning(
            "cross-seed: %d candidates exceed the deep-check cap (%d); checking only the first %d",
            len(candidate_ids),
            max_deep_checks,
            max_deep_checks,
        )
        candidate_ids = candidate_ids[:max_deep_checks]

    candidates: list[Torrent] = []
    for cid in candidate_ids:
        try:
            candidates.append(await target_client.torrents.get(cid))
        except GazelleNotFoundError:
            continue
    return candidates


async def cross_seed(
    source_client: GazelleClient,
    source_torrent_id: int,
    target_client: GazelleClient,
    *,
    max_deep_checks: int = DEFAULT_MAX_DEEP_CHECKS,
) -> CrossSeedResult | None:
    """Find ``source_torrent_id`` (on ``source_client``) on ``target_client`` and
    return the target's .torrent. Returns None when the source has no file list
    or no candidate exactly matches.
    """
    source = await source_client.torrents.get(source_torrent_id)
    if not source.files:
        logger.info("cross-seed: source torrent %d has no file list", source_torrent_id)
        return None

    candidates = await find_candidates(source, target_client, max_deep_checks=max_deep_checks)
    for candidate in candidates:
        if verify_match(source, candidate):
            torrent_file = await target_client.torrents.download(candidate.id)
            return CrossSeedResult(
                match=candidate,
                torrent_file=torrent_file,
                source_torrent_id=source_torrent_id,
                target_torrent_id=candidate.id,
            )
    return None
