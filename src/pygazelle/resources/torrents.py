from __future__ import annotations

from ..errors import GazelleAPIError
from ..models.torrents import Torrent, TorrentGroup, TorrentResult
from ..models.writes import LogAddition, TagAddition
from .base import BaseResource


class TorrentResource(BaseResource):
    async def get(self, torrent_id: int) -> Torrent:
        data = await self._transport.request("torrent", id=torrent_id)
        torrent_data = data.get("torrent")
        if torrent_data is None:
            raise GazelleAPIError(status_code=200, message="missing 'torrent' key in response")
        return Torrent.model_validate({**torrent_data, "group": data.get("group")})

    async def get_group(self, group_id: int) -> TorrentGroup:
        data = await self._transport.request("torrentgroup", id=group_id)
        group_data = data.get("group")
        if group_data is None:
            raise GazelleAPIError(status_code=200, message="missing 'group' key in response")
        # Use `or []` not a .get default: the API may send "torrents": null, and
        # passing None would raise an opaque pydantic error instead.
        return TorrentGroup.model_validate({**group_data, "torrents": data.get("torrents") or []})

    async def search(self, query: str, **params: str | int) -> list[TorrentResult]:
        data = await self._transport.request("browse", searchstr=query, **params)
        return self._parse_list(data.get("results"), TorrentResult)

    async def download(self, torrent_id: int) -> bytes:
        return await self._transport.download(torrent_id)

    async def add_tag(self, group_id: int, tags: str | list[str]) -> TagAddition:
        """Add tag(s) to a torrent group (action=add_tag).

        ``tags`` may be a single tag, a comma-separated string, or a list of
        tags (joined into the comma-separated ``tagname`` the API expects).
        """
        tagname = tags if isinstance(tags, str) else ",".join(tags)
        data = await self._transport.request_write(
            "add_tag", data={"groupid": group_id, "tagname": tagname}
        )
        return TagAddition.model_validate(data)

    async def add_log(self, torrent_id: int, logfiles: bytes | list[bytes]) -> LogAddition:
        """Attach rip log file(s) to a torrent (action=add_log).

        The torrent id is a query param; the logs are multipart ``logfiles[]``.
        """
        blobs = [logfiles] if isinstance(logfiles, bytes) else list(logfiles)
        files = [("logfiles[]", (f"rip{i}.log", blob)) for i, blob in enumerate(blobs)]
        data = await self._transport.request_write(
            "add_log", params={"id": torrent_id}, files=files
        )
        return LogAddition.model_validate(data)
