from __future__ import annotations

from typing import Any

from ..models.artists import Artist, ArtistResult, SimilarArtist
from .base import BaseResource


class ArtistResource(BaseResource):
    async def get(self, artist_id: int) -> Artist:
        data = await self._transport.request("artist", id=artist_id)
        return Artist.model_validate(data)

    async def search(self, name: str) -> list[ArtistResult]:
        data = await self._transport.request("browse", searchstr=name, artistname=name)
        seen: dict[int, ArtistResult] = {}
        for result in data.get("results", []):
            artist_id = result.get("artistId")
            if artist_id is not None and artist_id not in seen:
                seen[artist_id] = ArtistResult(id=artist_id, name=result.get("artist", ""))
        return list(seen.values())

    async def similar(self, artist_id: int, limit: int | None = None) -> list[SimilarArtist]:
        params = self._params(id=artist_id, limit=limit)
        # similar_artists returns a bare JSON array (not a {results: ...} object);
        # request() is typed to return a dict, so treat the payload as untyped.
        raw: Any = await self._transport.request("similar_artists", **params)
        # `or []` guards a null response (artist with no similar artists).
        items: list[Any] = raw or []
        return [SimilarArtist.model_validate(a) for a in items]
