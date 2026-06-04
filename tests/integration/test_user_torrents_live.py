from pygazelle.client import OrpheusClient


async def test_user_torrents_single_live_read(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key, max_retries=0) as client:
        me = await client.user.me()
        results = await client.user.torrents(me.id, "uploaded", limit=5)
    assert isinstance(results, list)
