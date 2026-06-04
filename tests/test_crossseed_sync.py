from __future__ import annotations

from typing import Any

from pygazelle.client import GazelleClient
from pygazelle.crossseed import CrossSeedResult
from pygazelle.sync import GazelleSyncClient, cross_seed_sync
from tests.support import (
    CrossSeedTransport,
    make_browse_group,
    make_browse_row,
    make_torrent_payload,
)

_BASE: dict[str, Any] = dict(group_id=5, group_name="Album", year=2020, artist="Band")


def test_cross_seed_sync_returns_without_await():
    files = [("01.flac", 30)]
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
                torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)],
            )
        ],
        torrents={
            20: make_torrent_payload(torrent_id=20, file_path="Album [FLAC]", files=files, **_BASE)
        },
        download_bytes=b"sync-torrent",
    )
    source = GazelleSyncClient(GazelleClient(source_t))  # pyright: ignore[reportArgumentType]
    target = GazelleSyncClient(GazelleClient(target_t))  # pyright: ignore[reportArgumentType]
    try:
        result = cross_seed_sync(source, 1, target)
        assert isinstance(result, CrossSeedResult)
        assert result.torrent_file == b"sync-torrent"
        assert result.target_torrent_id == 20
    finally:
        source.close()
        target.close()
