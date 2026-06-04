from __future__ import annotations

from typing import Any

from pygazelle.errors import GazelleNotFoundError


def make_torrent_row(torrent_id: int) -> dict[str, Any]:
    """A minimal dict that validates as a pygazelle Torrent (all required fields)."""
    return {
        "id": torrent_id,
        "media": "CD",
        "format": "FLAC",
        "encoding": "Lossless",
        "scene": False,
        "hasLog": False,
        "hasCue": False,
        "logScore": 0,
        "fileCount": 1,
        "size": 1,
        "seeders": 1,
        "leechers": 0,
        "snatched": 0,
        "time": "2020-01-01 00:00:00",
        "filePath": "x",
        "userId": 1,
        "username": "uploader",
    }


def make_user_torrent_row(torrent_id: int, group_id: int, name: str) -> dict[str, Any]:
    """A dict that validates as a UserTorrent."""
    return {"torrentId": torrent_id, "groupId": group_id, "name": name}


class MonitorTransport:
    """Fake transport for monitor tests.

    pages: ``{type: [[rows_page0], [rows_page1], ...]}`` — each row is a
        ``user_torrents`` item dict (use ``make_user_torrent_row``). Offset is
        mapped to a page index via ``limit``.
    groups: ``{group_id: [torrent_id, ...]}`` — torrents currently in a group
        (used by ``torrentgroup`` lookups during classification).
    missing_groups: group ids whose ``torrentgroup`` lookup raises NotFound.
    fail_action: optional ``(action, exc)`` — raise ``exc`` whenever ``action``
        is requested (used to test atomic-commit-on-error).
    """

    def __init__(
        self,
        *,
        user_id: int = 1,
        pages: dict[str, list[list[dict[str, Any]]]] | None = None,
        groups: dict[int, list[int]] | None = None,
        missing_groups: tuple[int, ...] = (),
        fail_action: tuple[str, Exception] | None = None,
    ) -> None:
        self._user_id = user_id
        self._pages = pages or {}
        self._groups = groups or {}
        self._missing = set(missing_groups)
        self._fail_action = fail_action
        self.group_lookups: list[int] = []
        self._call_counts: dict[str, int] = {}

    async def request(self, action: str, **params: Any) -> Any:
        if self._fail_action and action == self._fail_action[0]:
            raise self._fail_action[1]
        if action == "index":
            return {"id": self._user_id, "username": "tester"}
        if action == "user_torrents":
            kind = params["type"]
            pages = self._pages.get(kind, [[]])
            idx = self._call_counts.get(kind, 0)
            # Sticky: once we've exhausted the pages list, keep returning the last page.
            idx = min(idx, len(pages) - 1) if pages else 0
            rows = pages[idx] if pages else []
            self._call_counts[kind] = idx + 1
            return {kind: rows, "total": sum(len(p) for p in pages)}
        if action == "torrentgroup":
            gid = params["id"]
            self.group_lookups.append(gid)
            if gid in self._missing:
                raise GazelleNotFoundError(f"group {gid} not found")
            tids = self._groups.get(gid, [])
            return {
                "group": {"id": gid, "name": f"Group {gid}", "year": 2020},
                "torrents": [make_torrent_row(t) for t in tids],
            }
        raise AssertionError(f"unexpected action: {action}")

    async def aclose(self) -> None:
        pass

    async def download(self, torrent_id: int) -> bytes:  # pragma: no cover - unused
        return b""


def make_torrent_payload(
    *,
    torrent_id: int,
    group_id: int,
    group_name: str,
    year: int,
    artist: str,
    file_path: str,
    files: list[tuple[str, int]],
    fmt: str = "FLAC",
    encoding: str = "Lossless",
    media: str = "CD",
) -> dict[str, Any]:
    """Build an action=torrent response ({"torrent": ..., "group": ...}) that
    validates as a Torrent with a file list and group metadata.

    ``files`` is a list of (relative path, size) pairs.
    """
    file_list = "|||".join(f"{path}{{{{{{{size}}}}}}}" for path, size in files)
    total = sum(size for _, size in files)
    return {
        "torrent": {
            "id": torrent_id,
            "media": media,
            "format": fmt,
            "encoding": encoding,
            "scene": False,
            "hasLog": False,
            "hasCue": False,
            "logScore": 0,
            "fileCount": len(files),
            "size": total,
            "seeders": 1,
            "leechers": 0,
            "snatched": 0,
            "time": "2020-01-01 00:00:00",
            "filePath": file_path,
            "userId": 1,
            "username": "uploader",
            "fileList": file_list,
        },
        "group": {
            "id": group_id,
            "name": group_name,
            "year": year,
            "musicInfo": {"artists": [{"id": 1, "name": artist}]},
        },
    }


def make_browse_row(
    *,
    torrent_id: int,
    size: int,
    file_count: int,
    fmt: str = "FLAC",
    encoding: str = "Lossless",
    media: str = "CD",
) -> dict[str, Any]:
    """A BrowseTorrent row inside a browse group result."""
    return {
        "torrentId": torrent_id,
        "size": size,
        "fileCount": file_count,
        "format": fmt,
        "encoding": encoding,
        "media": media,
    }


def make_browse_group(
    *,
    group_id: int,
    group_name: str,
    artist: str,
    year: int,
    torrents: list[dict[str, Any]],
) -> dict[str, Any]:
    """A browse result group (action=browse 'results' entry)."""
    return {
        "groupId": group_id,
        "groupName": group_name,
        "artist": artist,
        "groupYear": year,
        "maxSize": max((t["size"] for t in torrents), default=0),
        "totalSeeders": 1,
        "totalLeechers": 0,
        "totalSnatched": 0,
        "torrents": torrents,
    }


class UploadTransport:
    """Fake transport for cross-upload tests. request_write records the upload
    call (self.writes) and returns upload_response; no real network."""

    def __init__(
        self,
        *,
        passkey: str | None = None,
        announce_host: str | None = None,
        index: dict[str, Any] | None = None,
        torrents: dict[int, dict[str, Any]] | None = None,
        browse_results: list[dict[str, Any]] | None = None,
        upload_response: dict[str, Any] | None = None,
        user_id: int = 1,
    ) -> None:
        self.announce_host = announce_host
        self._passkey = passkey
        self._index = index
        self._torrents = torrents or {}
        self._browse_results = browse_results or []
        self._upload_response = upload_response or {}
        self._user_id = user_id
        self.writes: list[dict[str, Any]] = []

    async def request(self, action: str, **params: Any) -> Any:
        if action == "index":
            return self._index or {"id": self._user_id, "username": "tester", "passkey": self._passkey}
        if action == "torrent":
            from pygazelle.errors import GazelleNotFoundError

            tid = params["id"]
            if tid not in self._torrents:
                raise GazelleNotFoundError(f"torrent {tid} not found")
            return self._torrents[tid]
        if action == "browse":
            return {"results": self._browse_results}
        raise AssertionError(f"unexpected read action: {action}")

    async def request_write(
        self,
        action: str,
        *,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, Any] | None = None,
        include_auth_key: bool = True,
    ) -> Any:
        self.writes.append({"action": action, "data": data, "files": files, "params": params})
        return self._upload_response

    async def download(self, torrent_id: int) -> bytes:  # pragma: no cover - unused here
        return b""

    async def aclose(self) -> None:
        pass


class CrossSeedTransport:
    """Fake transport for one side (source or target) of a cross-seed test.

    torrents: {id: action=torrent response} (use make_torrent_payload).
    browse_results: list of browse group dicts (use make_browse_group); returned
        for any 'browse' action regardless of params.
    download_bytes: bytes returned by download().
    """

    def __init__(
        self,
        *,
        torrents: dict[int, dict[str, Any]] | None = None,
        browse_results: list[dict[str, Any]] | None = None,
        download_bytes: bytes = b"torrent-file-bytes",
    ) -> None:
        self._torrents = torrents or {}
        self._browse_results = browse_results or []
        self._download_bytes = download_bytes
        self.downloaded: list[int] = []
        self.torrent_gets: list[int] = []

    async def request(self, action: str, **params: Any) -> Any:
        if action == "torrent":
            tid = params["id"]
            self.torrent_gets.append(tid)
            from pygazelle.errors import GazelleNotFoundError

            if tid not in self._torrents:
                raise GazelleNotFoundError(f"torrent {tid} not found")
            return self._torrents[tid]
        if action == "browse":
            return {"results": self._browse_results}
        raise AssertionError(f"unexpected action: {action}")

    async def aclose(self) -> None:
        pass

    async def download(self, torrent_id: int) -> bytes:
        self.downloaded.append(torrent_id)
        return self._download_bytes
