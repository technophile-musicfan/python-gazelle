from pygazelle.models.torrents import Torrent


def test_torrent_model_parses_orpheus_fixture(orpheus_torrent):
    torrent = Torrent.model_validate(orpheus_torrent["torrent"])
    assert isinstance(torrent.id, int)
    assert isinstance(torrent.format, str)
    assert isinstance(torrent.size, int)
    # Orpheus omits these fields; they parse as None rather than raising.
    assert torrent.info_hash is None
    assert torrent.remastered is None
    # Orpheus reports freeleech state as a string enum.
    assert torrent.free_torrent == "Normal"


def test_torrent_model_parses_redacted_fixture(redacted_torrent):
    torrent = Torrent.model_validate(redacted_torrent["torrent"])
    assert isinstance(torrent.id, int)
    assert isinstance(torrent.format, str)
