from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar, Unpack, final

from .client import GazelleClient, OrpheusClient, RedactedClient
from .transport import TransportOptions

_T = TypeVar("_T")


@final
class _BackgroundLoop:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._started: threading.Event = threading.Event()
        self._thread: threading.Thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._started.wait()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()

    def run(self, coro: Coroutine[Any, Any, _T], timeout: float | None = None) -> _T:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)


@final
class _SyncProxy:
    """Wraps a resource object, making every async method callable synchronously."""

    def __init__(self, resource: object, loop: _BackgroundLoop) -> None:
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_loop", loop)

    def __getattr__(self, name: str) -> Any:
        resource = object.__getattribute__(self, "_resource")
        loop = object.__getattribute__(self, "_loop")
        attr = getattr(resource, name)
        if inspect.iscoroutinefunction(attr):

            def sync_method(*args: object, **kwargs: object) -> object:
                return loop.run(attr(*args, **kwargs))

            return sync_method
        return attr


class GazelleSyncClient:
    def __init__(self, async_client: GazelleClient) -> None:
        self._async: GazelleClient = async_client
        self._bg: _BackgroundLoop = _BackgroundLoop()

    @property
    def torrents(self) -> _SyncProxy:
        return _SyncProxy(self._async.torrents, self._bg)

    @property
    def artists(self) -> _SyncProxy:
        return _SyncProxy(self._async.artists, self._bg)

    @property
    def requests(self) -> _SyncProxy:
        return _SyncProxy(self._async.requests, self._bg)

    @property
    def collages(self) -> _SyncProxy:
        return _SyncProxy(self._async.collages, self._bg)

    @property
    def user(self) -> _SyncProxy:
        return _SyncProxy(self._async.user, self._bg)

    @property
    def inbox(self) -> _SyncProxy:
        return _SyncProxy(self._async.inbox, self._bg)

    @property
    def notifications(self) -> _SyncProxy:
        return _SyncProxy(self._async.notifications, self._bg)

    @property
    def bookmarks(self) -> _SyncProxy:
        return _SyncProxy(self._async.bookmarks, self._bg)

    @property
    def subscriptions(self) -> _SyncProxy:
        return _SyncProxy(self._async.subscriptions, self._bg)

    def close(self) -> None:
        self._bg.run(self._async.aclose())
        self._bg.stop()


class OrpheusClientSync(GazelleSyncClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: Unpack[TransportOptions],
    ) -> None:
        super().__init__(
            OrpheusClient(username=username, password=password, api_key=api_key, **kwargs)
        )


class RedactedClientSync(GazelleSyncClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: Unpack[TransportOptions],
    ) -> None:
        super().__init__(
            RedactedClient(username=username, password=password, api_key=api_key, **kwargs)
        )
