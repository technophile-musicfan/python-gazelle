from __future__ import annotations

from ..models.collages import Collage
from .base import BaseResource


class CollageResource(BaseResource):
    async def get(self, collage_id: int) -> Collage:
        data = await self._transport.request("collage", id=collage_id)
        return Collage.model_validate(data)
