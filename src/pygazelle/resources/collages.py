from .base import BaseResource
from ..models.collages import Collage


class CollageResource(BaseResource):
    async def get(self, collage_id: int) -> Collage:
        data = await self._transport.request("collage", id=collage_id)
        return Collage.model_validate(data)
