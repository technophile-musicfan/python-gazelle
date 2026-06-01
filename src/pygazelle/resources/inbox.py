from __future__ import annotations

from ..models.inbox import Message
from .base import BaseResource


class InboxResource(BaseResource):
    async def list(self, **params: str | int) -> list[Message]:
        data = await self._transport.request("inbox", type="inbox", **params)
        return [Message.model_validate(m) for m in data.get("messages", [])]

    async def get(self, conversation_id: int) -> list[Message]:
        data = await self._transport.request("inbox", type="viewconv", id=conversation_id)
        return [Message.model_validate(m) for m in data.get("messages", [])]
