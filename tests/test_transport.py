import time

import httpx
import pytest

from pygazelle.errors import (
    GazelleAPIError,
    GazelleAuthError,
    GazelleNotFoundError,
    GazelleRateLimitError,
)
from pygazelle.transport import GazelleTransport, TokenBucket


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


def make_transport(
    responses: list[tuple[int, dict | bytes]], **kwargs
) -> tuple[GazelleTransport, MockTransport]:
    mock = MockTransport(responses)
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com", api_key="test", _http_client=client, **kwargs
    )
    return transport, mock


async def test_request_returns_response_dict():
    transport, _ = make_transport(
        [
            (200, {"status": "success", "response": {"id": 1, "name": "Album"}}),
        ]
    )
    async with transport:
        result = await transport.request("torrent", id=1)
    assert result == {"id": 1, "name": "Album"}


async def test_request_raises_on_failure_status():
    transport, _ = make_transport(
        [
            (200, {"status": "failure", "error": "bad id parameter"}),
        ]
    )
    async with transport:
        with pytest.raises(GazelleAPIError):
            await transport.request("torrent", id=999)


async def test_request_raises_not_found_on_404():
    transport, _ = make_transport([(404, b"")])
    async with transport:
        with pytest.raises(GazelleNotFoundError):
            await transport.request("torrent", id=999)


async def test_request_sends_action_as_query_param():
    transport, mock = make_transport(
        [
            (200, {"status": "success", "response": {}}),
        ]
    )
    async with transport:
        await transport.request("index")
    assert b"action=index" in mock.requests[0].url.query


async def test_download_returns_bytes():
    transport, _ = make_transport([(200, b"torrent-data")])
    async with transport:
        result = await transport.download(42)
    assert result == b"torrent-data"


async def test_api_key_sent_as_authorization_header():
    transport, mock = make_transport(
        [
            (200, {"status": "success", "response": {}}),
        ]
    )
    async with transport:
        await transport.request("index")
    assert mock.requests[0].headers.get("authorization") == "token test"


async def test_api_key_prefix_can_be_overridden_to_bare_key():
    # RED expects the bare key with no "token " prefix.
    transport, mock = make_transport(
        [
            (200, {"status": "success", "response": {}}),
        ],
        api_key_prefix="",
    )
    async with transport:
        await transport.request("index")
    assert mock.requests[0].headers.get("authorization") == "test"


async def test_cookie_auth_calls_login_on_first_request():
    mock = MockTransport(
        [
            (200, b""),  # login POST
            (200, {"status": "success", "response": {"id": 1}}),  # API call
        ]
    )
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
    mock = MockTransport(
        [
            (200, b""),  # initial login
            (401, b""),  # 401 on first API call → triggers re-auth
            (200, b""),  # re-login
            (200, {"status": "success", "response": {"id": 99}}),  # retry succeeds
        ]
    )
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


async def test_request_write_posts_action_and_injects_auth_key():
    transport, mock = make_transport(
        [
            (200, {"status": "success", "response": {"authkey": "AK123"}}),  # index
            (200, {"status": "success", "response": {"ok": True}}),  # write POST
        ]
    )
    async with transport:
        result = await transport.request_write("add_tag", data={"groupid": 1, "tagname": "rock"})
    assert result == {"ok": True}
    # First call fetches the authkey via GET index, then POSTs the write.
    assert mock.requests[0].method == "GET"
    assert b"action=index" in mock.requests[0].url.query
    write = mock.requests[1]
    assert write.method == "POST"
    assert b"action=add_tag" in write.url.query
    assert b"groupid=1" in write.content
    assert b"tagname=rock" in write.content
    assert b"auth=AK123" in write.content


async def test_request_write_caches_auth_key_across_calls():
    transport, mock = make_transport(
        [
            (200, {"status": "success", "response": {"authkey": "AK123"}}),  # index (once)
            (200, {"status": "success", "response": {"ok": 1}}),  # write 1
            (200, {"status": "success", "response": {"ok": 2}}),  # write 2
        ]
    )
    async with transport:
        await transport.request_write("add_tag", data={"groupid": 1})
        await transport.request_write("add_tag", data={"groupid": 2})
    # index fetched exactly once; the two writes reuse the cached authkey.
    assert [r.method for r in mock.requests] == ["GET", "POST", "POST"]
    assert sum(b"action=index" in r.url.query for r in mock.requests) == 1


async def test_request_write_does_not_retry_on_500():
    transport, mock = make_transport([(500, b"")], max_retries=3)
    async with transport:
        with pytest.raises(GazelleAPIError):
            await transport.request_write("add_tag", data={"groupid": 1}, include_auth_key=False)
    # Non-idempotent: exactly one attempt, no retry despite max_retries=3.
    assert mock._index == 1


async def test_request_write_does_not_retry_on_429():
    transport, mock = make_transport([(429, b"")], max_retries=3)
    async with transport:
        with pytest.raises(GazelleRateLimitError):
            await transport.request_write("add_tag", data={"groupid": 1}, include_auth_key=False)
    assert mock._index == 1


async def test_request_write_surfaces_failure_message():
    transport, _ = make_transport(
        [(200, {"status": "failure", "error": "you cannot add that tag"})]
    )
    async with transport:
        with pytest.raises(GazelleAPIError):
            await transport.request_write("add_tag", data={"groupid": 1}, include_auth_key=False)


async def test_request_write_does_not_overwrite_explicit_auth():
    transport, mock = make_transport([(200, {"status": "success", "response": {"ok": True}})])
    async with transport:
        await transport.request_write("add_tag", data={"groupid": 1, "auth": "MINE"})
    # Caller supplied auth → no index fetch, only the single POST.
    assert len(mock.requests) == 1
    assert mock.requests[0].method == "POST"
    assert b"auth=MINE" in mock.requests[0].content


async def test_request_write_supports_multipart_files():
    transport, mock = make_transport([(200, {"status": "success", "response": {"ok": True}})])
    async with transport:
        await transport.request_write(
            "upload",
            data={"groupid": 1},
            files={"file_input": ("a.torrent", b"d8:announce")},
            include_auth_key=False,
        )
    assert mock.requests[0].headers["content-type"].startswith("multipart/form-data")


async def test_request_write_reauths_once_on_cookie_401():
    mock = MockTransport(
        [
            (200, b""),  # initial login
            (401, b""),  # write rejected — session expired (never processed)
            (200, b""),  # re-login
            (200, {"status": "success", "response": {"ok": True}}),  # write retried
        ]
    )
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com", username="u", password="p", _http_client=client
    )
    async with transport:
        result = await transport.request_write(
            "add_tag", data={"groupid": 1}, include_auth_key=False
        )
    assert result == {"ok": True}


async def test_request_write_does_not_resend_on_403():
    # 403 is "forbidden", not an expired session — the write must not be
    # re-sent (only 401 triggers a single re-auth).
    mock = MockTransport(
        [
            (200, b""),  # initial login
            (403, b""),  # write forbidden
        ]
    )
    client = httpx.AsyncClient(transport=mock)
    transport = GazelleTransport(
        "https://example.com", username="u", password="p", _http_client=client
    )
    async with transport:
        with pytest.raises(GazelleAuthError):
            await transport.request_write("add_tag", data={"groupid": 1}, include_auth_key=False)
    # login + single write attempt, no re-auth resend.
    assert len(mock.requests) == 2


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
    transport, mock = make_transport(
        [
            (429, b""),
            (429, b""),
            (200, {"status": "success", "response": {"ok": True}}),
        ],
        max_retries=3,
    )
    async with transport:
        result = await transport.request("index")
    assert result == {"ok": True}
    assert mock._index == 3


async def test_retries_on_500():
    transport, mock = make_transport(
        [
            (500, b""),
            (200, {"status": "success", "response": {"ok": True}}),
        ],
        max_retries=3,
    )
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
