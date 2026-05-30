import pytest

from pygazelle.models.torrents import Torrent


@pytest.mark.xfail(
    strict=True,
    reason="python-gazelle-6ue: Orpheus 'torrent' diverges — infoHash/remastered "
    "absent and freeTorrent is a string enum ('Normal'), not bool.",
)
def test_torrent_model_parses_orpheus_fixture(orpheus_torrent):
    torrent = Torrent.model_validate(orpheus_torrent["torrent"])
    assert isinstance(torrent.id, int)
    assert isinstance(torrent.format, str)
    assert isinstance(torrent.size, int)


def test_torrent_model_parses_redacted_fixture(redacted_torrent):
    torrent = Torrent.model_validate(redacted_torrent["torrent"])
    assert isinstance(torrent.id, int)
    assert isinstance(torrent.format, str)
