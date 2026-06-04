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
