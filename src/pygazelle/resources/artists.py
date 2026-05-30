from .base import BaseResource
from ..models.artists import Artist, ArtistResult


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
