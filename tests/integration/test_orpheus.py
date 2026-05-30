from pygazelle.client import OrpheusClient
from pygazelle.models import User, Notification


async def test_orpheus_api_key_auth_returns_user(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key) as client:
        user = await client.user.me()
    assert isinstance(user, User)
    assert isinstance(user.id, int)
    assert isinstance(user.username, str)


async def test_orpheus_cookie_auth_returns_user(orpheus_credentials):
    username, password = orpheus_credentials
    async with OrpheusClient(username=username, password=password) as client:
        user = await client.user.me()
    assert isinstance(user, User)
    assert isinstance(user.username, str)


async def test_orpheus_notifications_list(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key) as client:
        notifications = await client.notifications.list()
    assert isinstance(notifications, list)
    for n in notifications:
        assert isinstance(n, Notification)


async def test_orpheus_torrent_search_returns_results(orpheus_api_key):
    async with OrpheusClient(api_key=orpheus_api_key) as client:
        results = await client.torrents.search("", format="FLAC")
    assert isinstance(results, list)
    assert len(results) > 0
