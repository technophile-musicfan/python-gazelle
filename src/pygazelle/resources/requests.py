from __future__ import annotations

from ..models.requests import Request, RequestResult
from ..models.writes import RequestFill
from .base import BaseResource


class RequestResource(BaseResource):
    async def get(self, request_id: int) -> Request:
        data = await self._transport.request("request", id=request_id)
        return Request.model_validate(data)

    async def search(self, query: str, **params: str | int) -> list[RequestResult]:
        data = await self._transport.request("requests", search=query, **params)
        return [RequestResult.model_validate(r) for r in data.get("results", [])]

    async def fill(
        self,
        request_id: int,
        *,
        torrent_id: int | None = None,
        link: str | None = None,
        user: str | None = None,
    ) -> RequestFill:
        """Mark a request filled (action=request_fill).

        Provide either ``torrent_id`` or a ``link`` to the filling torrent;
        ``user`` is mod-only. Raises ``ValueError`` if neither is given.
        """
        if torrent_id is None and link is None:
            raise ValueError("request_fill requires either torrent_id or link")
        body = self._params(requestid=request_id, torrentid=torrent_id, link=link, user=user)
        data = await self._transport.request_write("request_fill", data=body)
        return RequestFill.model_validate(data)
