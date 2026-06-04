from pygazelle.crossseed import CrossSeedResult, verify_match
from pygazelle.models.torrents import Torrent
from tests.support import make_torrent_payload


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


def _torrent(**kw: object) -> Torrent:
    p = make_torrent_payload(**kw)  # type: ignore[arg-type]
    return Torrent.model_validate({**p["torrent"], "group": p["group"]})


_BASE = dict(group_id=5, group_name="Album", year=2020, artist="Band")


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
