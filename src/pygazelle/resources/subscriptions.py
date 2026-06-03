from __future__ import annotations

from typing import Any

from ..models.subscriptions import ForumSubscription
from .base import BaseResource


class SubscriptionResource(BaseResource):
    async def list(self) -> list[ForumSubscription]:
        data = await self._transport.request("subscriptions")
        items: list[Any] = data.get("threads") or []
        return [ForumSubscription.model_validate(t) for t in items]
