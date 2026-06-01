from __future__ import annotations

from ..errors import GazelleAPIError
from ..models.torrents import Torrent, TorrentResult
from .base import BaseResource


class TorrentResource(BaseResource):
    async def get(self, torrent_id: int) -> Torrent:
        data = await self._transport.request("torrent", id=torrent_id)
        torrent_data = data.get("torrent")
        if torrent_data is None:
            raise GazelleAPIError(status_code=200, message="missing 'torrent' key in response")
        return Torrent.model_validate({**torrent_data, "group": data.get("group")})

    async def search(self, query: str, **params: str | int) -> list[TorrentResult]:
        data = await self._transport.request("browse", searchstr=query, **params)
        return [TorrentResult.model_validate(r) for r in data.get("results", [])]

    async def download(self, torrent_id: int) -> bytes:
        return await self._transport.download(torrent_id)
