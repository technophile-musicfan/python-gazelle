"""Capture real API response fixtures for model testing. Run once with valid credentials."""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


async def capture(
    tracker: str, base_url: str, api_key: str, api_key_prefix: str = "token "
) -> None:
    from pygazelle.transport import GazelleTransport

    out = FIXTURE_DIR / tracker
    out.mkdir(parents=True, exist_ok=True)

    async with GazelleTransport(
        base_url, api_key=api_key, api_key_prefix=api_key_prefix, rate=1.0
    ) as t:
        index = await t.request("index")
        (out / "index.json").write_text(
            json.dumps({"status": "success", "response": index}, indent=2)
        )
        print(f"[{tracker}] Captured index")

        notifications = await t.request("notifications")
        (out / "notifications.json").write_text(
            json.dumps({"status": "success", "response": notifications}, indent=2)
        )
        print(f"[{tracker}] Captured notifications")

        # Get a torrent ID from a search to fetch as fixture
        browse = await t.request("browse", searchstr="", format="FLAC", page=1)
        results = browse.get("results", [])
        torrent = None
        if results and results[0].get("torrents"):
            torrent_id = results[0]["torrents"][0]["torrentId"]
            torrent = await t.request("torrent", id=torrent_id)
            (out / "torrent.json").write_text(
                json.dumps({"status": "success", "response": torrent}, indent=2)
            )
            print(f"[{tracker}] Captured torrent {torrent_id}")

        # Fetch the full group (all editions) for the same release.
        if torrent:
            group_id = torrent.get("group", {}).get("id")
            if group_id:
                torrentgroup = await t.request("torrentgroup", id=group_id)
                (out / "torrentgroup.json").write_text(
                    json.dumps({"status": "success", "response": torrentgroup}, indent=2)
                )
                print(f"[{tracker}] Captured torrentgroup {group_id}")

        # Capture the current user's uploaded + snatched lists (action=user_torrents).
        # `index` above carries the user id under "id".
        user_id = index.get("id")
        if user_id:
            for kind in ("uploaded", "snatched"):
                user_torrents = await t.request(
                    "user_torrents", id=user_id, type=kind, limit=50, offset=0
                )
                (out / f"user_torrents_{kind}.json").write_text(
                    json.dumps({"status": "success", "response": user_torrents}, indent=2)
                )
                print(f"[{tracker}] Captured user_torrents ({kind})")

        # Derive an artist fixture from the torrent's group musicInfo.
        artist_id = None
        if torrent:
            artists = torrent.get("group", {}).get("musicInfo", {}).get("artists") or []
            if artists:
                artist_id = artists[0].get("id")
        if artist_id:
            artist = await t.request("artist", id=artist_id)
            (out / "artist.json").write_text(
                json.dumps({"status": "success", "response": artist}, indent=2)
            )
            print(f"[{tracker}] Captured artist {artist_id}")

            similar = await t.request("similar_artists", id=artist_id, limit=10)
            (out / "similar_artists.json").write_text(
                json.dumps({"status": "success", "response": similar}, indent=2)
            )
            print(f"[{tracker}] Captured similar_artists for {artist_id}")
        else:
            print(f"[{tracker}] WARNING: no artist id found, artist fixture skipped")


async def main() -> None:
    # Reuse the canonical base URLs (and RED's bare-key auth) from the client
    # so the capture tool can't drift from the library config.
    from pygazelle.client import ORPHEUS_BASE_URL, REDACTED_BASE_URL

    orpheus_key = os.getenv("ORPHEUS_API_KEY")
    redacted_key = os.getenv("REDACTED_API_KEY")
    if orpheus_key:
        await capture("orpheus", ORPHEUS_BASE_URL, orpheus_key)
    if redacted_key:
        await capture("redacted", REDACTED_BASE_URL, redacted_key, api_key_prefix="")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
