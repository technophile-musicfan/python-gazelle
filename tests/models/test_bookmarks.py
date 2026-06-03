from pygazelle.models.bookmarks import (
    BookmarkedArtist,
    BookmarkedTorrentGroup,
)


def test_bookmarked_torrent_group_parses_nested_torrents():
    group = BookmarkedTorrentGroup.model_validate(
        {
            "id": 1,
            "name": "Album",
            "year": 2020,
            "tagList": "rock electronic",
            "releaseType": "Album",
            "torrents": [{"id": 100, "groupId": 1, "format": "FLAC"}],
        }
    )
    assert group.id == 1
    assert group.tag_list == "rock electronic"
    assert group.torrents[0].id == 100
    assert group.torrents[0].group_id == 1


def test_bookmarked_torrent_group_empty_torrents_default():
    group = BookmarkedTorrentGroup.model_validate({"id": 1, "name": "Album"})
    assert group.torrents == []


def test_bookmarked_artist_aliases():
    artist = BookmarkedArtist.model_validate({"artistId": 5, "artistName": "Radiohead"})
    assert artist.artist_id == 5
    assert artist.artist_name == "Radiohead"
