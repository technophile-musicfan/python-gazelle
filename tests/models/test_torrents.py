from pygazelle.models.torrents import (
    BrowseTorrent,
    Torrent,
    TorrentFile,
    TorrentGroup,
    TorrentResult,
)


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


def test_torrent_edition_fields_orpheus(orpheus_torrent):
    torrent = Torrent.model_validate(orpheus_torrent["torrent"])
    assert torrent.remaster_year == 2025
    assert torrent.remaster_title == ""
    assert torrent.remaster_record_label == "More Hate Productions"
    assert torrent.remaster_catalogue_number == "MHP 25-530"
    assert torrent.description == ""
    # Log detail + freeleech reason are Orpheus-only in the torrent block.
    assert torrent.log_checksum is True
    assert torrent.log_count == 1
    assert torrent.rip_log_ids == [903694]
    assert torrent.free_reason == "Normal"
    assert torrent.reported is False


def test_torrent_edition_fields_redacted(redacted_torrent):
    torrent = Torrent.model_validate(redacted_torrent["torrent"])
    assert torrent.remaster_year == 2026
    assert torrent.remaster_record_label == "SM Entertainment"
    assert torrent.rip_log_ids == []
    assert torrent.reported is False
    assert torrent.description is not None
    assert torrent.description.startswith("[color")
    # RED omits these (Orpheus-only) -> tolerant None.
    assert torrent.log_checksum is None
    assert torrent.log_count is None
    assert torrent.free_reason is None


def test_torrent_edition_fields_default_none_when_absent():
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
    assert torrent.remaster_year is None
    assert torrent.remaster_title is None
    assert torrent.description is None
    assert torrent.log_checksum is None
    assert torrent.log_count is None
    assert torrent.rip_log_ids == []
    assert torrent.free_reason is None
    assert torrent.reported is None


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


def test_torrentgroup_populates_artists_from_music_info():
    # action=torrentgroup (and the embedded group) carry artists under
    # musicInfo.artists with no top-level "artists" key.
    group = TorrentGroup.model_validate(
        {
            "id": 7,
            "name": "Album",
            "year": 2020,
            "tags": ["rock"],
            "musicInfo": {"artists": [{"id": 3, "name": "Radiohead"}]},
        }
    )
    assert [a.name for a in group.artists] == ["Radiohead"]
    assert group.torrents == []


def test_torrentgroup_explicit_artists_take_precedence():
    group = TorrentGroup.model_validate(
        {
            "id": 7,
            "name": "Album",
            "year": 2020,
            "artists": [{"id": 1, "name": "Explicit"}],
            "musicInfo": {"artists": [{"id": 3, "name": "FromMusicInfo"}]},
        }
    )
    assert [a.name for a in group.artists] == ["Explicit"]


def test_torrentgroup_explicit_empty_artists_not_overwritten():
    # An explicit empty list is a caller decision; musicInfo must not stomp it.
    group = TorrentGroup.model_validate(
        {
            "id": 7,
            "name": "Album",
            "year": 2020,
            "artists": [],
            "musicInfo": {"artists": [{"id": 3, "name": "FromMusicInfo"}]},
        }
    )
    assert group.artists == []


def test_torrentgroup_model_parses_orpheus_fixture(orpheus_torrentgroup):
    group = TorrentGroup.model_validate(
        {**orpheus_torrentgroup["group"], "torrents": orpheus_torrentgroup.get("torrents", [])}
    )
    assert isinstance(group.id, int)
    assert group.torrents, "expected editions in torrents[]"
    assert all(isinstance(t, Torrent) for t in group.torrents)
    # Orpheus surfaces artists via musicInfo.
    assert group.artists


def test_torrentgroup_model_parses_redacted_fixture(redacted_torrentgroup):
    group = TorrentGroup.model_validate(
        {**redacted_torrentgroup["group"], "torrents": redacted_torrentgroup.get("torrents", [])}
    )
    assert isinstance(group.id, int)
    assert group.torrents
    assert all(isinstance(t, Torrent) for t in group.torrents)


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
