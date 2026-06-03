from __future__ import annotations

from typing import Any

from ..models.bookmarks import BookmarkedArtist, BookmarkedTorrentGroup
from .base import BaseResource


class BookmarkResource(BaseResource):
    async def torrents(self) -> list[BookmarkedTorrentGroup]:
        data = await self._transport.request("bookmarks", type="torrents")
        items: list[Any] = data.get("bookmarks") or []
        return [BookmarkedTorrentGroup.model_validate(g) for g in items]

    async def artists(self) -> list[BookmarkedArtist]:
        data = await self._transport.request("bookmarks", type="artists")
        items: list[Any] = data.get("artists") or []
        return [BookmarkedArtist.model_validate(a) for a in items]
