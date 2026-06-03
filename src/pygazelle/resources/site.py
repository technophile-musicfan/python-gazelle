from __future__ import annotations

from typing import Literal

from ..models.site import Announcements, Top10Category
from .base import BaseResource

Top10Type = Literal["torrents", "tags", "users"]


class SiteResource(BaseResource):
    async def top10(
        self, type: Top10Type = "torrents", limit: int | None = None
    ) -> list[Top10Category]:
        params = self._params(type=type, limit=limit)
        # top10 returns a bare JSON array of category objects.
        data = await self._transport.request("top10", **params)
        return self._parse_list(data, Top10Category)

    async def announcements(self) -> Announcements:
        data = await self._transport.request("announcements")
        return Announcements.model_validate(data)
