from pygazelle.client import RedactedClient
from pygazelle.models import User, Notification


async def test_redacted_api_key_auth_returns_user(redacted_api_key):
    async with RedactedClient(api_key=redacted_api_key) as client:
        user = await client.user.me()
    assert isinstance(user, User)
    assert isinstance(user.id, int)


async def test_redacted_cookie_auth_returns_user(redacted_credentials):
    username, password = redacted_credentials
    async with RedactedClient(username=username, password=password) as client:
        user = await client.user.me()
    assert isinstance(user, User)


async def test_redacted_notifications_list(redacted_api_key):
    async with RedactedClient(api_key=redacted_api_key) as client:
        notifications = await client.notifications.list()
    assert isinstance(notifications, list)


async def test_redacted_torrent_search_returns_results(redacted_api_key):
    async with RedactedClient(api_key=redacted_api_key) as client:
        results = await client.torrents.search("", format="FLAC")
    assert isinstance(results, list)
    assert len(results) > 0
