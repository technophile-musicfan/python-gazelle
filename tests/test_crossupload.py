from __future__ import annotations

from pygazelle.crossupload import DuplicateMatch, UploadDraft, UploadResult


def test_dataclasses_hold_fields():
    dup = DuplicateMatch(torrent_id=7, group_id=3, kind="exact", name="Band - Album")
    draft = UploadDraft(
        form={"title": "Album"},
        unmapped=["release_type"],
        warnings=["release type 21 has no equivalent"],
        duplicates=[dup],
        torrent_file=b"data",
        source_torrent_id=1,
        target_tracker="redacted",
    )
    assert draft.form["title"] == "Album"
    assert draft.unmapped == ["release_type"]
    assert draft.duplicates[0].kind == "exact"
    draft.form["release_type"] = 1
    assert draft.form["release_type"] == 1
    res = UploadResult(torrent_id=99, group_id=42, url="https://red/torrents.php?id=42")
    assert res.torrent_id == 99


from pygazelle.client import GazelleClient
from tests.support import UploadTransport


async def test_announce_url_built_from_passkey_and_host():
    transport = UploadTransport(passkey="abc123", announce_host="flacsfor.me")
    client = GazelleClient(transport)  # pyright: ignore[reportArgumentType]
    url = await client.user.announce_url()
    assert url == "https://flacsfor.me/abc123/announce"


from pygazelle.crossupload import map_metadata
from pygazelle.models.torrents import Torrent
from tests.support import make_torrent_payload


def _src(release_type: int = 1, tags: tuple[str, ...] = ("rock",)) -> Torrent:
    p = make_torrent_payload(
        torrent_id=1,
        group_id=5,
        group_name="Album",
        year=2020,
        artist="Band",
        file_path="Album [FLAC]",
        files=[("01.flac", 30)],
    )
    p["group"]["releaseType"] = release_type
    p["group"]["tags"] = list(tags)
    return Torrent.model_validate({**p["torrent"], "group": p["group"]})


def test_map_metadata_direct_fields():
    mapped = map_metadata(_src(), "redacted")
    assert mapped.fields["title"] == "Album"
    assert mapped.fields["year"] == 2020
    assert mapped.fields["artists"] == ["Band"]
    assert mapped.fields["format"] == "FLAC"


def test_map_metadata_release_type_table_hit():
    mapped = map_metadata(_src(release_type=1), "redacted")
    assert "release_type" not in mapped.unmapped
    assert "release_type" in mapped.fields


def test_map_metadata_release_type_miss_flags_unmapped():
    mapped = map_metadata(_src(release_type=9999), "redacted")
    assert "release_type" in mapped.unmapped
    assert any("release type" in w.lower() for w in mapped.warnings)
    assert "release_type" not in mapped.fields


def test_map_metadata_tags_warned():
    mapped = map_metadata(_src(tags=("rock", "obscure.subgenre")), "redacted")
    assert mapped.fields.get("tags")
    assert any("tag" in w.lower() for w in mapped.warnings)
