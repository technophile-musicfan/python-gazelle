from __future__ import annotations

from typing import Literal

from ..errors import GazelleError
from ..models.user import User, UserProfile, UserSearchResult, UserTorrent
from .base import BaseResource

UserTorrentType = Literal[
    "uploaded",
    "uploaded-unseeded",
    "seeding",
    "leeching",
    "snatched",
    "snatched-unseeded",
    "downloaded",
]


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
        return self._parse_list(data.get("results"), UserSearchResult)

    async def torrents(
        self,
        user_id: int,
        type: UserTorrentType,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[UserTorrent]:
        params = self._params(id=user_id, type=type, limit=limit, offset=offset)
        data = await self._transport.request("user_torrents", **params)
        # The torrents list is keyed under the requested type (e.g. "seeding": [...]).
        return self._parse_list(data.get(type), UserTorrent)

    async def announce_url(self) -> str:
        """The current user's announce URL on this tracker (passkey + announce host)."""
        me = await self.me()
        host = self._transport.announce_host
        if not me.passkey or not host:
            raise GazelleError("announce URL unavailable: missing passkey or announce host")
        return f"https://{host}/{me.passkey}/announce"
