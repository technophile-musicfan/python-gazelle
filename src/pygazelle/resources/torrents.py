from .base import BaseResource
from ..models.torrents import Torrent, TorrentResult


class TorrentResource(BaseResource):
    async def get(self, torrent_id: int) -> Torrent:
        data = await self._transport.request("torrent", id=torrent_id)
        return Torrent.model_validate({**data["torrent"], "group": data.get("group")})

    async def search(self, query: str, **params: str | int) -> list[TorrentResult]:
        data = await self._transport.request("browse", searchstr=query, **params)
        return [TorrentResult.model_validate(r) for r in data.get("results", [])]

    async def download(self, torrent_id: int) -> bytes:
        return await self._transport.download(torrent_id)
