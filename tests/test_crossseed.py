from pygazelle.crossseed import CrossSeedResult


def test_cross_seed_result_holds_fields():
    r = CrossSeedResult(
        match=None,  # type: ignore[arg-type]  # placeholder; real match is a Torrent
        torrent_file=b"data",
        source_torrent_id=1,
        target_torrent_id=2,
    )
    assert r.torrent_file == b"data"
    assert r.source_torrent_id == 1
    assert r.target_torrent_id == 2
    assert r.confidence == "exact"
