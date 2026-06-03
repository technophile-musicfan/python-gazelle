from __future__ import annotations

from ..models.bookmarks import BookmarkedArtist, BookmarkedTorrentGroup
from .base import BaseResource


class BookmarkResource(BaseResource):
    async def torrents(self) -> list[BookmarkedTorrentGroup]:
        data = await self._transport.request("bookmarks", type="torrents")
        return self._parse_list(data.get("bookmarks"), BookmarkedTorrentGroup)

    async def artists(self) -> list[BookmarkedArtist]:
        data = await self._transport.request("bookmarks", type="artists")
        return self._parse_list(data.get("artists"), BookmarkedArtist)
