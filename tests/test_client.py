from pygazelle.models import Artist, Notification, Torrent, User
from pygazelle.resources.artists import ArtistResource
from pygazelle.resources.notifications import NotificationResource
from pygazelle.resources.torrents import TorrentResource
from pygazelle.resources.user import UserResource


class StubTransport:
    def __init__(self, responses: dict[str, dict]) -> None:
        self._responses = responses

    async def request(self, action: str, **params) -> dict:
        return self._responses[action]

    async def download(self, torrent_id: int) -> bytes:
        return b"fake-torrent-data"


async def test_torrent_resource_get_returns_torrent_model():
    stub = StubTransport(
        {
            "torrent": {
                "group": {"id": 1, "name": "Album", "year": 2020, "tags": [], "artists": []},
                "torrent": {
                    "id": 100,
                    "infoHash": "ABC",
                    "media": "CD",
                    "format": "FLAC",
                    "encoding": "Lossless",
                    "remastered": False,
                    "scene": False,
                    "hasLog": True,
                    "hasCue": True,
                    "logScore": 100,
                    "fileCount": 12,
                    "size": 500000000,
                    "seeders": 10,
                    "leechers": 1,
                    "snatched": 50,
                    "freeTorrent": False,
                    "time": "2020-01-01 00:00:00",
                    "filePath": "Artist - Album",
                    "userId": 1,
                    "username": "uploader",
                },
            }
        }
    )
    resource = TorrentResource(stub)
    torrent = await resource.get(100)
    assert isinstance(torrent, Torrent)
    assert torrent.id == 100
    assert torrent.format == "FLAC"


async def test_torrent_resource_download_returns_bytes():
    stub = StubTransport({})
    resource = TorrentResource(stub)
    data = await resource.download(100)
    assert data == b"fake-torrent-data"


async def test_artist_resource_get_returns_artist_model():
    stub = StubTransport(
        {"artist": {"id": 1, "name": "Radiohead", "body": "", "image": "", "tags": []}}
    )
    resource = ArtistResource(stub)
    artist = await resource.get(1)
    assert isinstance(artist, Artist)
    assert artist.name == "Radiohead"


async def test_user_resource_me_returns_user_model():
    stub = StubTransport(
        {
            "index": {
                "id": 42,
                "username": "myuser",
                "userstats": {
                    "uploaded": 1000,
                    "downloaded": 500,
                    "ratio": 2.0,
                    "requiredRatio": 0.6,
                },
            }
        }
    )
    resource = UserResource(stub)
    user = await resource.me()
    assert isinstance(user, User)
    assert user.username == "myuser"


async def test_user_resource_me_without_required_ratio():
    # Orpheus omits requiredRatio; the model must still validate.
    stub = StubTransport(
        {
            "index": {
                "id": 42,
                "username": "myuser",
                "userstats": {"uploaded": 1000, "downloaded": 500, "ratio": 2.0},
            }
        }
    )
    resource = UserResource(stub)
    user = await resource.me()
    assert user.userstats is not None
    assert user.userstats.required_ratio is None


async def test_notification_resource_list_returns_notifications():
    stub = StubTransport(
        {
            "notifications": {
                "results": [
                    {
                        "torrentId": 1,
                        "torrentGroupId": 10,
                        "groupName": "Album",
                        "format": "FLAC",
                        "notificationType": "Upload Deleted",
                    }
                ]
            }
        }
    )
    resource = NotificationResource(stub)
    notifications = await resource.list()
    assert len(notifications) == 1
    assert isinstance(notifications[0], Notification)
    assert notifications[0].notification_type == "Upload Deleted"


import httpx as _httpx

from pygazelle.client import GazelleClient, OrpheusClient, RedactedClient
from pygazelle.resources.artists import ArtistResource as _ArtistResource
from pygazelle.resources.notifications import NotificationResource as _NotificationResource
from pygazelle.resources.torrents import TorrentResource as _TorrentResource
from pygazelle.transport import GazelleTransport as _GazelleTransport


class _FakeHttpTransport(_httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: _httpx.Request) -> _httpx.Response:
        return _httpx.Response(200, json={"status": "success", "response": {}})


def _make_client() -> GazelleClient:
    http = _httpx.AsyncClient(transport=_FakeHttpTransport())
    transport = _GazelleTransport("https://example.com", api_key="k", _http_client=http)
    return GazelleClient(transport)


def test_client_exposes_resource_namespaces():
    client = _make_client()
    assert isinstance(client.torrents, _TorrentResource)
    assert isinstance(client.artists, _ArtistResource)
    assert isinstance(client.notifications, _NotificationResource)
    assert hasattr(client, "requests")
    assert hasattr(client, "collages")
    assert hasattr(client, "user")
    assert hasattr(client, "inbox")


def test_orpheus_client_uses_orpheus_url():
    client = OrpheusClient(api_key="k")
    assert "orpheus.network" in client._transport._ajax_url


def test_redacted_client_uses_redacted_url():
    client = RedactedClient(api_key="k")
    assert "redacted.sh" in client._transport._ajax_url


def test_orpheus_client_uses_token_prefixed_auth_header():
    client = OrpheusClient(api_key="k")
    assert client._transport._client.headers.get("authorization") == "token k"


def test_redacted_client_uses_bare_key_auth_header():
    client = RedactedClient(api_key="k")
    assert client._transport._client.headers.get("authorization") == "k"
