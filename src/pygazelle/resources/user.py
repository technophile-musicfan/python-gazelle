from __future__ import annotations

from ..models.user import User
from .base import BaseResource


class UserResource(BaseResource):
    async def me(self) -> User:
        data = await self._transport.request("index")
        return User.model_validate(data)
