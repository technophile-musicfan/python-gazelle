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
