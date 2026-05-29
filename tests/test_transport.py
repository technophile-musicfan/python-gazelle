import time
import pytest
import httpx
from pygazelle.transport import GazelleTransport, TokenBucket
from pygazelle.errors import GazelleAPIError, GazelleNotFoundError, GazelleRateLimitError


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


async def test_token_bucket_allows_first_request_immediately():
    bucket = TokenBucket(rate=3.0)
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1  # no wait for first token


async def test_token_bucket_with_high_rate_does_not_wait():
    bucket = TokenBucket(rate=1000.0)
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1


async def test_transport_respects_custom_rate():
    # With rate=1000, 5 requests should complete nearly instantly
    transport, mock = make_transport(
        [(200, {"status": "success", "response": {}}) for _ in range(5)],
        rate=1000.0,
    )
    start = time.monotonic()
    async with transport:
        for _ in range(5):
            await transport.request("index")
    elapsed = time.monotonic() - start
    assert elapsed < 1.0


async def test_retries_on_429():
    transport, mock = make_transport([
        (429, b""),
        (429, b""),
        (200, {"status": "success", "response": {"ok": True}}),
    ], max_retries=3)
    async with transport:
        result = await transport.request("index")
    assert result == {"ok": True}
    assert mock._index == 3


async def test_retries_on_500():
    transport, mock = make_transport([
        (500, b""),
        (200, {"status": "success", "response": {"ok": True}}),
    ], max_retries=3)
    async with transport:
        result = await transport.request("index")
    assert result == {"ok": True}


async def test_raises_rate_limit_error_after_max_retries():
    transport, _ = make_transport(
        [(429, b"")] * 4,
        max_retries=3,
    )
    async with transport:
        with pytest.raises(GazelleRateLimitError):
            await transport.request("index")


async def test_does_not_retry_on_404():
    transport, mock = make_transport([(404, b""), (200, {"status": "success", "response": {}})])
    async with transport:
        with pytest.raises(GazelleNotFoundError):
            await transport.request("torrent", id=1)
    assert mock._index == 1  # only one request made
