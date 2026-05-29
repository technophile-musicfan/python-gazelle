import pytest
import httpx
from pygazelle.transport import GazelleTransport
from pygazelle.errors import GazelleAPIError, GazelleNotFoundError


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[tuple[int, dict | bytes]]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._responses[self._index % len(self._responses)]
        self._index += 1
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)


def make_transport(responses: list[tuple[int, dict | bytes]], **kwargs) -> tuple[GazelleTransport, MockTransport]:
    mock = MockTransport(responses)
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport("https://example.com", api_key="test", _http_client=client, **kwargs)
    return transport, mock


async def test_request_returns_response_dict():
    transport, _ = make_transport([
        (200, {"status": "success", "response": {"id": 1, "name": "Album"}}),
    ])
    async with transport:
        result = await transport.request("torrent", id=1)
    assert result == {"id": 1, "name": "Album"}


async def test_request_raises_on_failure_status():
    transport, _ = make_transport([
        (200, {"status": "failure", "error": "bad id parameter"}),
    ])
    async with transport:
        with pytest.raises(GazelleAPIError):
            await transport.request("torrent", id=999)


async def test_request_raises_not_found_on_404():
    transport, _ = make_transport([(404, b"")])
    async with transport:
        with pytest.raises(GazelleNotFoundError):
            await transport.request("torrent", id=999)


async def test_request_sends_action_as_query_param():
    transport, mock = make_transport([
        (200, {"status": "success", "response": {}}),
    ])
    async with transport:
        await transport.request("index")
    assert b"action=index" in mock.requests[0].url.query


async def test_download_returns_bytes():
    transport, _ = make_transport([(200, b"torrent-data")])
    async with transport:
        result = await transport.download(42)
    assert result == b"torrent-data"


async def test_api_key_sent_as_authorization_header():
    transport, mock = make_transport([
        (200, {"status": "success", "response": {}}),
    ])
    async with transport:
        await transport.request("index")
    assert mock.requests[0].headers.get("authorization") == "token test"


async def test_cookie_auth_calls_login_on_first_request():
    mock = MockTransport([
        (200, b""),                                          # login POST
        (200, {"status": "success", "response": {"id": 1}}),  # API call
    ])
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com",
        username="user",
        password="pass",
        _http_client=client,
    )
    async with transport:
        result = await transport.request("index")
    assert len(mock.requests) == 2
    assert mock.requests[0].method == "POST"
    assert result == {"id": 1}


async def test_cookie_auth_reauths_on_401():
    mock = MockTransport([
        (200, b""),    # initial login
        (401, b""),    # 401 on first API call → triggers re-auth
        (200, b""),    # re-login
        (200, {"status": "success", "response": {"id": 99}}),  # retry succeeds
    ])
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com",
        username="user",
        password="pass",
        _http_client=client,
    )
    async with transport:
        result = await transport.request("index")
    assert result == {"id": 99}
