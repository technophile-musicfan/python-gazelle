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


def test_torrentgroup_release_type_name_orpheus(orpheus_torrent):
    group = TorrentGroup.model_validate(orpheus_torrent["group"])
    assert group.release_type == 1
    assert group.release_type_name == "Album"
    assert group.proxy_image is not None
    assert group.wiki_bbcode is not None
    assert group.is_bookmarked is False
    assert group.time == "2026-05-30 10:44:54"


def test_torrentgroup_extras_redacted(redacted_torrent):
    group = TorrentGroup.model_validate(redacted_torrent["group"])
    # RED omits releaseTypeName and proxyImage.
    assert group.release_type_name is None
    assert group.proxy_image is None
    # RED carries the BBcode body under "bbBody" (Orpheus uses "wikiBBcode").
    assert group.wiki_bbcode is not None
    assert group.is_bookmarked is False
    assert group.time is not None


def test_torrentgroup_extras_default_none_when_absent():
    group = TorrentGroup.model_validate({"id": 1, "name": "X", "year": 2020})
    assert group.release_type_name is None
    assert group.proxy_image is None
    assert group.wiki_bbcode is None
    assert group.is_bookmarked is None
    assert group.time is None


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


def test_browse_torrent_enriched_orpheus(orpheus_browse):
    result = TorrentResult.model_validate(orpheus_browse["results"][0])
    t = result.torrents[0]
    assert t.edition_id == 1
    assert t.has_log is True
    assert t.log_score == 100
    assert t.has_cue is True
    assert t.scene is False
    assert t.seeders == 7
    assert t.leechers == 0
    assert t.snatches == 6
    assert t.remaster_year == 2025
    assert t.remaster_record_label == "More Hate Productions"
    assert t.is_freeleech is False
    assert t.can_use_token is True
    assert t.has_snatched is False
    assert t.artists[0].name == "Dead Point"


def test_browse_torrent_enriched_redacted(redacted_browse):
    result = TorrentResult.model_validate(redacted_browse["results"][0])
    t = result.torrents[0]
    assert t.edition_id == 1
    assert t.seeders == 8
    assert t.snatches == 8
    assert t.remaster_year == 2026
    assert t.is_freeleech is False
    assert t.has_snatched is False
    assert t.artists[0].name == "aespa (에스파)"


def test_browse_result_group_extras_orpheus(orpheus_browse):
    result = TorrentResult.model_validate(orpheus_browse["results"][0])
    assert result.cover is not None
    assert result.bookmarked is False
    assert result.vanity_house is False
    assert result.group_time == "2026-05-30 10:44:54"
    assert result.release_type == "Album"


def test_browse_result_group_extras_redacted(redacted_browse):
    result = TorrentResult.model_validate(redacted_browse["results"][0])
    assert result.cover is not None
    assert result.release_type == "Remix"
    assert result.group_time is not None


def test_browse_enrichment_defaults_when_absent():
    result = TorrentResult.model_validate(
        {
            "groupId": 1,
            "groupName": "G",
            "artist": "A",
            "groupYear": 2020,
            "maxSize": 0,
            "totalSeeders": 0,
            "totalLeechers": 0,
            "totalSnatched": 0,
            "torrents": [
                {
                    "torrentId": 1,
                    "size": 0,
                    "fileCount": 0,
                    "format": "FLAC",
                    "encoding": "Lossless",
                    "media": "CD",
                }
            ],
        }
    )
    assert result.cover is None
    assert result.bookmarked is None
    assert result.release_type is None
    assert result.group_time is None
    t = result.torrents[0]
    assert t.edition_id is None
    assert t.artists == []
    assert t.is_freeleech is None
    assert t.seeders is None
