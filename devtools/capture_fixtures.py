"""Capture real API response fixtures for model testing. Run once with valid credentials."""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


async def capture(tracker: str, base_url: str, api_key: str) -> None:
    from pygazelle.transport import GazelleTransport

    out = FIXTURE_DIR / tracker
    out.mkdir(parents=True, exist_ok=True)

    async with GazelleTransport(base_url, api_key=api_key, rate=1.0) as t:
        index = await t.request("index")
        (out / "index.json").write_text(json.dumps({"status": "success", "response": index}, indent=2))
        print(f"[{tracker}] Captured index")

        notifications = await t.request("notifications")
        (out / "notifications.json").write_text(json.dumps({"status": "success", "response": notifications}, indent=2))
        print(f"[{tracker}] Captured notifications")

        # Get a torrent ID from a search to fetch as fixture
        browse = await t.request("browse", searchstr="", format="FLAC", page=1)
        results = browse.get("results", [])
        if results and results[0].get("torrents"):
            torrent_id = results[0]["torrents"][0]["torrentId"]
            torrent = await t.request("torrent", id=torrent_id)
            (out / "torrent.json").write_text(json.dumps({"status": "success", "response": torrent}, indent=2))
            print(f"[{tracker}] Captured torrent {torrent_id}")

        # Get an artist fixture
        if results:
            artist_data = results[0].get("artists")
            if artist_data:
                artist_id = artist_data[0]["id"] if isinstance(artist_data, list) else None
                if artist_id:
                    artist = await t.request("artist", id=artist_id)
                    (out / "artist.json").write_text(json.dumps({"status": "success", "response": artist}, indent=2))
                    print(f"[{tracker}] Captured artist {artist_id}")


async def main() -> None:
    orpheus_key = os.getenv("ORPHEUS_API_KEY")
    redacted_key = os.getenv("REDACTED_API_KEY")
    if orpheus_key:
        await capture("orpheus", "https://orpheus.network", orpheus_key)
    if redacted_key:
        await capture("redacted", "https://redacted.ch", redacted_key)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
