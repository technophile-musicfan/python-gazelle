from pygazelle.models.collages import Collage
from pygazelle.models.torrents import TorrentGroup


def test_collage_parses_basic_fields():
    c = Collage.model_validate({"id": 5, "name": "Best Of", "description": "d", "numTorrents": 3})
    assert c.id == 5
    assert c.name == "Best Of"
    assert c.num_torrents == 3


def test_collage_exposes_torrent_groups():
    # action=collage returns a "torrentgroups" array, each entry shaped like
    # action=torrentgroup (id/name/year + nested torrents).
    c = Collage.model_validate(
        {
            "id": 5,
            "name": "Best Of",
            "torrentgroups": [
                {
                    "id": 1607112,
                    "name": "Endangered Specie",
                    "year": 2025,
                    "releaseType": 1,
                    "tags": ["death.metal"],
                    "torrents": [
                        {
                            "id": 3637388,
                            "media": "CD",
                            "format": "FLAC",
                            "encoding": "Lossless",
                            "scene": False,
                            "hasLog": True,
                            "hasCue": True,
                            "logScore": 100,
                            "fileCount": 29,
                            "size": 472046588,
                            "seeders": 7,
                            "leechers": 0,
                            "snatched": 6,
                            "time": "2026-05-30 10:44:54",
                            "filePath": "Dead Point - 2025 - Endangered Specie",
                            "userId": 36973,
                            "username": "CamaradaD",
                        }
                    ],
                }
            ],
        }
    )
    assert len(c.torrent_groups) == 1
    group = c.torrent_groups[0]
    assert isinstance(group, TorrentGroup)
    assert group.id == 1607112
    assert group.year == 2025
    assert group.torrents[0].format == "FLAC"


def test_collage_torrent_groups_default_empty_when_absent():
    c = Collage.model_validate({"id": 5, "name": "Best Of"})
    assert c.torrent_groups == []
