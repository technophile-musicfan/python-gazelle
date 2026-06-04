from __future__ import annotations

import pytest

import pygazelle
from pygazelle.client import GazelleClient
from pygazelle.crossupload import (
    DuplicateMatch,
    TrackerKind,
    UploadDraft,
    UploadResult,
    duplicate_check,
    map_metadata,
    prepare_upload,
    submit_upload,
)
from pygazelle.errors import GazelleNotFoundError
from pygazelle.models.torrents import Torrent
from tests.support import (
    UploadTransport,
    make_browse_group,
    make_browse_row,
    make_torrent_payload,
)


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


async def test_announce_url_built_from_passkey_and_host():
    transport = UploadTransport(passkey="abc123", announce_host="flacsfor.me")
    client = GazelleClient(transport)  # pyright: ignore[reportArgumentType]
    url = await client.user.announce_url()
    assert url == "https://flacsfor.me/abc123/announce"


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


def _client(t):
    return GazelleClient(t)  # pyright: ignore[reportArgumentType]


async def test_duplicate_check_exact():
    files = [("01.flac", 30)]
    source = _src()
    target = UploadTransport(
        browse_results=[
            make_browse_group(
                group_id=9,
                group_name="Album",
                artist="Band",
                year=2020,
                torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)],
            )
        ],
        torrents={
            20: make_torrent_payload(
                torrent_id=20,
                group_id=9,
                group_name="Album",
                year=2020,
                artist="Band",
                file_path="Album [FLAC]",
                files=files,
            )
        },
    )
    dupes = await duplicate_check(source, _client(target))
    assert [(d.torrent_id, d.kind) for d in dupes] == [(20, "exact")]


async def test_duplicate_check_possible():
    source = _src()
    target = UploadTransport(
        browse_results=[
            make_browse_group(
                group_id=9,
                group_name="Album",
                artist="Band",
                year=2020,
                torrents=[make_browse_row(torrent_id=20, size=30, file_count=1)],
            )
        ],
        torrents={
            20: make_torrent_payload(
                torrent_id=20,
                group_id=9,
                group_name="Album",
                year=2020,
                artist="Band",
                file_path="DIFFERENT",
                files=[("01.flac", 30)],
            )
        },
    )
    dupes = await duplicate_check(source, _client(target))
    assert [(d.torrent_id, d.kind) for d in dupes] == [(20, "possible")]


async def test_duplicate_check_none():
    assert await duplicate_check(_src(), _client(UploadTransport(browse_results=[]))) == []


def _complete_draft(
    target: TrackerKind = "redacted", duplicates: list[DuplicateMatch] | None = None
) -> UploadDraft:
    return UploadDraft(
        form={
            "artists": ["Band"],
            "title": "Album",
            "year": 2020,
            "release_type": 1,
            "format": "FLAC",
            "bitrate": "Lossless",
            "media": "CD",
        },
        unmapped=[],
        warnings=[],
        duplicates=duplicates or [],
        torrent_file=b"tbytes",
        source_torrent_id=1,
        target_tracker=target,
    )


async def test_submit_refuses_missing_required_field():
    draft = _complete_draft()
    del draft.form["title"]
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    with pytest.raises(ValueError) as ei:
        await submit_upload(_client(target), draft)
    assert "title" in str(ei.value)
    assert target.writes == []


async def test_submit_refuses_on_exact_duplicate():
    draft = _complete_draft(
        duplicates=[DuplicateMatch(torrent_id=20, group_id=9, kind="exact", name="x")]
    )
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    with pytest.raises(ValueError):
        await submit_upload(_client(target), draft)
    assert target.writes == []


async def test_submit_allows_exact_duplicate_with_override():
    draft = _complete_draft(
        duplicates=[DuplicateMatch(torrent_id=20, group_id=9, kind="exact", name="x")]
    )
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    result = await submit_upload(_client(target), draft, allow_duplicate=True)
    assert isinstance(result, UploadResult)
    assert len(target.writes) == 1


async def test_submit_possible_duplicate_does_not_block():
    draft = _complete_draft(
        duplicates=[DuplicateMatch(torrent_id=20, group_id=9, kind="possible", name="x")]
    )
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    result = await submit_upload(_client(target), draft)
    assert result.torrent_id == 99


async def test_submit_happy_path_posts_multipart():
    draft = _complete_draft()
    target = UploadTransport(upload_response={"torrentid": 99, "groupid": 42})
    result = await submit_upload(_client(target), draft)
    assert result.torrent_id == 99 and result.group_id == 42
    write = target.writes[0]
    assert write["action"] == "upload"
    assert write["files"] is not None
    assert write["data"]["title"] == "Album"


async def test_prepare_upload_assembles_draft_no_writes():
    files = [("01.flac", 30)]
    src_payload = make_torrent_payload(
        torrent_id=1,
        group_id=5,
        group_name="Album",
        year=2020,
        artist="Band",
        file_path="Album [FLAC]",
        files=files,
    )
    src_payload["group"]["releaseType"] = 1
    source_t = UploadTransport(torrents={1: src_payload})
    target_t = UploadTransport(browse_results=[])  # no dupes
    draft = await prepare_upload(_client(source_t), 1, _client(target_t), torrent_file=b"tbytes")
    assert isinstance(draft, UploadDraft)
    assert draft.torrent_file == b"tbytes"
    assert draft.form["title"] == "Album"
    assert draft.duplicates == []
    assert target_t.writes == []  # READ-ONLY: prepare must not write


async def test_prepare_upload_source_not_found_raises():
    source_t = UploadTransport(torrents={})
    target_t = UploadTransport()
    with pytest.raises(GazelleNotFoundError):
        await prepare_upload(_client(source_t), 1, _client(target_t), torrent_file=b"x")


def test_public_exports():
    for name in (
        "prepare_upload",
        "submit_upload",
        "map_metadata",
        "duplicate_check",
        "UploadDraft",
        "UploadResult",
        "DuplicateMatch",
        "prepare_upload_sync",
        "submit_upload_sync",
    ):
        assert hasattr(pygazelle, name), name
        assert name in pygazelle.__all__, name
