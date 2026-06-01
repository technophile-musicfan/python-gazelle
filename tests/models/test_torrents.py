from pygazelle.models.torrents import BrowseTorrent, Torrent, TorrentFile, TorrentResult


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


def test_torrent_parses_file_list_orpheus(orpheus_torrent):
    torrent = Torrent.model_validate(orpheus_torrent["torrent"])
    files = torrent.files
    assert all(isinstance(f, TorrentFile) for f in files)
    assert ("01 - Predatory Nature.flac", 13820961) in [(f.path, f.size) for f in files]
    # extras are preserved (F2 filters them, not the parser)
    assert any(f.path.endswith(".log") for f in files)


def test_torrent_file_list_html_unescaped_redacted(redacted_torrent):
    torrent = Torrent.model_validate(redacted_torrent["torrent"])
    names = [f.path for f in torrent.files]
    # The raw fileList contains "&rsquo;" and "&#39;"; the parser decodes them.
    assert "10. ’Til We Die.flac" in names
    assert not any("&rsquo;" in n or "&#39;" in n for n in names)


def test_torrent_files_empty_when_no_file_list():
    torrent = Torrent.model_validate(
        {
            "id": 1,
            "media": "CD",
            "format": "FLAC",
            "encoding": "Lossless",
            "scene": False,
            "hasLog": False,
            "hasCue": False,
            "logScore": 0,
            "fileCount": 0,
            "size": 0,
            "seeders": 0,
            "leechers": 0,
            "snatched": 0,
            "freeTorrent": False,
            "time": "t",
            "filePath": "p",
            "userId": 1,
            "username": "u",
        }
    )
    assert torrent.files == []


def test_torrent_exposes_trumpable_orpheus(orpheus_torrent):
    torrent = Torrent.model_validate(orpheus_torrent["torrent"])
    assert torrent.trumpable is False
    assert torrent.trumpable_reasons == []


def test_torrent_trumpable_defaults_when_absent():
    torrent = Torrent.model_validate(
        {
            "id": 1,
            "media": "CD",
            "format": "FLAC",
            "encoding": "Lossless",
            "scene": False,
            "hasLog": False,
            "hasCue": False,
            "logScore": 0,
            "fileCount": 0,
            "size": 0,
            "seeders": 0,
            "leechers": 0,
            "snatched": 0,
            "freeTorrent": False,
            "time": "t",
            "filePath": "p",
            "userId": 1,
            "username": "u",
        }
    )
    assert torrent.trumpable is None
    assert torrent.trumpable_reasons == []


def test_browse_result_parses_nested_torrents_orpheus(orpheus_browse):
    results = orpheus_browse["results"]
    assert results, "fixture has no results"
    result = TorrentResult.model_validate(results[0])
    assert result.torrents, "expected nested torrents[]"
    t = result.torrents[0]
    assert isinstance(t, BrowseTorrent)
    assert isinstance(t.torrent_id, int)
    assert isinstance(t.size, int)
    assert isinstance(t.file_count, int)
    assert isinstance(t.format, str)


def test_browse_result_parses_nested_torrents_redacted(redacted_browse):
    results = redacted_browse["results"]
    assert results, "fixture has no results"
    result = TorrentResult.model_validate(results[0])
    assert result.torrents
    assert isinstance(result.torrents[0].torrent_id, int)
