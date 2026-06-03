from __future__ import annotations

from typing import Any

from ..models.user import User, UserProfile, UserSearchResult, UserTorrent
from .base import BaseResource


class UserResource(BaseResource):
    async def me(self) -> User:
        data = await self._transport.request("index")
        return User.model_validate(data)

    async def get(self, user_id: int) -> UserProfile:
        data = await self._transport.request("user", id=user_id)
        # The API omits the id (it's the request param); inject it for the model.
        return UserProfile.model_validate({**data, "id": user_id})

    async def search(self, query: str, **params: str | int) -> list[UserSearchResult]:
        data = await self._transport.request("usersearch", search=query, **params)
        return [UserSearchResult.model_validate(r) for r in data.get("results", [])]

    async def torrents(
        self, user_id: int, type: str, limit: int | None = None, offset: int | None = None
    ) -> list[UserTorrent]:
        params: dict[str, str | int] = {"id": user_id, "type": type}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._transport.request("user_torrents", **params)
        # The torrents list is keyed under the requested type (e.g. "seeding": [...]).
        items: list[Any] = data.get(type) or []
        return [UserTorrent.model_validate(t) for t in items]
