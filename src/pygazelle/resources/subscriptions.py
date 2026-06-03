from __future__ import annotations

from ..models.subscriptions import ForumSubscription
from .base import BaseResource


class SubscriptionResource(BaseResource):
    async def list(self) -> list[ForumSubscription]:
        data = await self._transport.request("subscriptions")
        return self._parse_list(data.get("threads"), ForumSubscription)
