from .base import BaseResource
from ..models.notifications import Notification


class NotificationResource(BaseResource):
    async def list(self, **params: str | int) -> list[Notification]:
        data = await self._transport.request("notifications", **params)
        return [Notification.model_validate(n) for n in data.get("results", [])]
