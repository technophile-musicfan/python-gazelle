from __future__ import annotations

from typing import Any

from pygazelle.client import GazelleClient
from pygazelle.crossseed import CrossSeedResult, find_candidates, verify_match
from pygazelle.models.torrents import Torrent
from tests.support import (
    CrossSeedTransport,
    make_browse_group,
    make_browse_row,
    make_torrent_payload,
)


def test_cross_seed_result_holds_fields():
    r = CrossSeedResult(
        match=None,  # pyright: ignore[reportArgumentType]  # placeholder; real match is a Torrent
        torrent_file=b"data",
        source_torrent_id=1,
        target_torrent_id=2,
    )
    assert r.torrent_file == b"data"
    assert r.source_torrent_id == 1
    assert r.target_torrent_id == 2
    assert r.confidence == "exact"


def _torrent(**kw: Any) -> Torrent:
    p = make_torrent_payload(**kw)
    return Torrent.model_validate({**p["torrent"], "group": p["group"]})


_BASE: dict[str, Any] = dict(group_id=5, group_name="Album", year=2020, artist="Band")


def test_verify_match_identical_passes_any_order() -> None:
    src = _torrent(
        torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE
    )
    cand = _torrent(
        torrent_id=2, file_path="Album [FLAC]", files=[("02.flac", 28), ("01.flac", 30)], **_BASE
    )
    assert verify_match(src, cand) is True


def test_verify_match_differing_top_folder_rejects() -> None:
    src = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    cand = _torrent(
        torrent_id=2, file_path="Band - Album (2020) [FLAC]", files=[("01.flac", 30)], **_BASE
    )
    assert verify_match(src, cand) is False


def test_verify_match_differing_size_rejects() -> None:
    src = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    cand = _torrent(torrent_id=2, file_path="Album [FLAC]", files=[("01.flac", 31)], **_BASE)
    assert verify_match(src, cand) is False


def test_verify_match_missing_file_rejects() -> None:
    src = _torrent(
        torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE
    )
    cand = _torrent(torrent_id=2, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    assert verify_match(src, cand) is False


def test_verify_match_empty_filelists_do_not_match() -> None:
    src = _torrent(torrent_id=1, file_path="X", files=[], **_BASE)
    cand = _torrent(torrent_id=2, file_path="X", files=[], **_BASE)
    assert verify_match(src, cand) is False


def _client(transport: object) -> GazelleClient:
    return GazelleClient(transport)  # pyright: ignore[reportArgumentType]


async def test_find_candidates_prefilters_wrong_format():
    source = _torrent(
        torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30), ("02.flac", 28)], **_BASE
    )
    target = CrossSeedTransport(
        browse_results=[
            make_browse_group(
                group_id=9,
                group_name="Album",
                artist="Band",
                year=2020,
                torrents=[
                    make_browse_row(torrent_id=20, size=58, file_count=2),
                    make_browse_row(
                        torrent_id=21, size=58, file_count=2, fmt="MP3", encoding="320"
                    ),
                    make_browse_row(torrent_id=22, size=99, file_count=2),
                ],
            )
        ],
        torrents={
            20: make_torrent_payload(
                torrent_id=20,
                file_path="Album [FLAC]",
                files=[("01.flac", 30), ("02.flac", 28)],
                **_BASE,
            ),
        },
    )
    candidates = await find_candidates(source, _client(target))
    assert target.torrent_gets == [20]
    assert [c.id for c in candidates] == [20]


async def test_find_candidates_groupname_fallback_when_no_artist_hits():
    source = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    target = CrossSeedTransport(
        browse_results=[
            make_browse_group(
                group_id=9,
                group_name="Album",
                artist="Band",
                year=2020,
                torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)],
            )
        ],
        torrents={
            20: make_torrent_payload(
                torrent_id=20, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE
            )
        },
    )
    candidates = await find_candidates(source, _client(target))
    assert [c.id for c in candidates] == [20]


async def test_find_candidates_caps_deep_checks():
    source = _torrent(torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE)
    rows = [make_browse_row(torrent_id=100 + i, size=30, file_count=1) for i in range(10)]
    torrents = {
        100 + i: make_torrent_payload(
            torrent_id=100 + i, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE
        )
        for i in range(10)
    }
    target = CrossSeedTransport(
        browse_results=[
            make_browse_group(
                group_id=9, group_name="Album", artist="Band", year=2020, torrents=rows
            )
        ],
        torrents=torrents,
    )
    candidates = await find_candidates(source, _client(target), max_deep_checks=3)
    assert len(target.torrent_gets) == 3
    assert len(candidates) == 3


from pygazelle.crossseed import cross_seed


async def test_cross_seed_happy_path_returns_torrent_bytes():
    files = [("01.flac", 30), ("02.flac", 28)]
    source_t = CrossSeedTransport(
        torrents={
            1: make_torrent_payload(torrent_id=1, file_path="Album [FLAC]", files=files, **_BASE)
        }
    )
    target_t = CrossSeedTransport(
        browse_results=[
            make_browse_group(
                group_id=9,
                group_name="Album",
                artist="Band",
                year=2020,
                torrents=[make_browse_row(torrent_id=20, size=58, file_count=2)],
            )
        ],
        torrents={
            20: make_torrent_payload(torrent_id=20, file_path="Album [FLAC]", files=files, **_BASE)
        },
        download_bytes=b"the-torrent",
    )
    result = await cross_seed(_client(source_t), 1, _client(target_t))
    assert result is not None
    assert result.torrent_file == b"the-torrent"
    assert result.source_torrent_id == 1
    assert result.target_torrent_id == 20
    assert result.confidence == "exact"
    assert target_t.downloaded == [20]


async def test_cross_seed_no_filelist_match_returns_none():
    source_t = CrossSeedTransport(
        torrents={
            1: make_torrent_payload(
                torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE
            )
        }
    )
    target_t = CrossSeedTransport(
        browse_results=[
            make_browse_group(
                group_id=9,
                group_name="Album",
                artist="Band",
                year=2020,
                torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)],
            )
        ],
        torrents={
            20: make_torrent_payload(
                torrent_id=20, file_path="DIFFERENT", files=[("01.flac", 30)], **_BASE
            )
        },
    )
    assert await cross_seed(_client(source_t), 1, _client(target_t)) is None
    assert target_t.downloaded == []


async def test_cross_seed_source_without_filelist_returns_none():
    source_t = CrossSeedTransport(
        torrents={1: make_torrent_payload(torrent_id=1, file_path="X", files=[], **_BASE)}
    )
    target_t = CrossSeedTransport()
    assert await cross_seed(_client(source_t), 1, _client(target_t)) is None


async def test_cross_seed_no_search_hits_returns_none():
    source_t = CrossSeedTransport(
        torrents={
            1: make_torrent_payload(
                torrent_id=1, file_path="Album [FLAC]", files=[("01.flac", 30)], **_BASE
            )
        }
    )
    target_t = CrossSeedTransport(browse_results=[])
    assert await cross_seed(_client(source_t), 1, _client(target_t)) is None


def test_public_exports_async():
    import pygazelle

    for name in ("cross_seed", "find_candidates", "verify_match", "CrossSeedResult"):
        assert hasattr(pygazelle, name), name
        assert name in pygazelle.__all__, name


def test_public_exports_sync():
    import pygazelle

    assert hasattr(pygazelle, "cross_seed_sync")
    assert "cross_seed_sync" in pygazelle.__all__
