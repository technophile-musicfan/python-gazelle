from __future__ import annotations

from ..models.requests import Request, RequestResult
from .base import BaseResource


class RequestResource(BaseResource):
    async def get(self, request_id: int) -> Request:
        data = await self._transport.request("request", id=request_id)
        return Request.model_validate(data)

    async def search(self, query: str, **params: str | int) -> list[RequestResult]:
        data = await self._transport.request("requests", search=query, **params)
        return [RequestResult.model_validate(r) for r in data.get("results", [])]
