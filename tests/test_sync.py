import httpx
from pygazelle.sync import GazelleSyncClient, OrpheusClientSync, RedactedClientSync
from pygazelle.client import GazelleClient
from pygazelle.transport import GazelleTransport
from pygazelle.models import User


class MockHttpTransport(httpx.AsyncBaseTransport):
    def __init__(self, response_json: dict) -> None:
        self._json = response_json

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=self._json)


def make_sync_client(response_json: dict) -> GazelleSyncClient:
    http = httpx.AsyncClient(transport=MockHttpTransport(response_json))
    transport = GazelleTransport("https://example.com", api_key="k", _http_client=http)
    return GazelleSyncClient(GazelleClient(transport))


def test_sync_client_returns_result_without_await():
    client = make_sync_client({
        "status": "success",
        "response": {
            "id": 1, "username": "user",
            "userstats": {"uploaded": 100, "downloaded": 50, "ratio": 2.0, "requiredRatio": 0.6},
        },
    })
    user = client.user.me()
    assert isinstance(user, User)
    assert user.username == "user"


def test_sync_client_background_thread_is_daemon():
    client = make_sync_client({"status": "success", "response": {}})
    assert client._bg._thread.daemon is True


def test_orpheus_client_sync_wraps_orpheus_client():
    client = OrpheusClientSync(api_key="k")
    assert "orpheus.network" in client._async._transport._ajax_url


def test_redacted_client_sync_wraps_redacted_client():
    client = RedactedClientSync(api_key="k")
    assert "redacted.ch" in client._async._transport._ajax_url


def test_sync_client_reuses_connection_across_calls():
    client = make_sync_client({
        "status": "success",
        "response": {"id": 1, "username": "u",
                     "userstats": {"uploaded": 0, "downloaded": 0, "ratio": 0.0, "requiredRatio": 0.0}},
    })
    for _ in range(3):
        user = client.user.me()
        assert isinstance(user, User)
