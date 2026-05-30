from .base import BaseResource
from ..models.user import User


class UserResource(BaseResource):
    async def me(self) -> User:
        data = await self._transport.request("index")
        return User.model_validate(data)
