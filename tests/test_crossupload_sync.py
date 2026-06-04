from __future__ import annotations

from pygazelle.client import GazelleClient
from pygazelle.crossupload import UploadDraft, UploadResult
from pygazelle.sync import GazelleSyncClient, prepare_upload_sync, submit_upload_sync
from tests.support import UploadTransport, make_torrent_payload


def test_prepare_and_submit_sync_no_await():
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
    source = GazelleSyncClient(GazelleClient(UploadTransport(torrents={1: src_payload})))  # pyright: ignore[reportArgumentType]
    target_t = UploadTransport(browse_results=[], upload_response={"torrentid": 99, "groupid": 42})
    target = GazelleSyncClient(GazelleClient(target_t))  # pyright: ignore[reportArgumentType]
    try:
        draft = prepare_upload_sync(source, 1, target, torrent_file=b"t")
        assert isinstance(draft, UploadDraft)
        for fld, val in {
            "artists": ["Band"],
            "title": "Album",
            "year": 2020,
            "release_type": 1,
            "format": "FLAC",
            "bitrate": "Lossless",
            "media": "CD",
        }.items():
            draft.form.setdefault(fld, val)
        result = submit_upload_sync(target, draft)
        assert isinstance(result, UploadResult)
    finally:
        source.close()
        target.close()
