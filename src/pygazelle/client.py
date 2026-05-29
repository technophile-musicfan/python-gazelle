from __future__ import annotations

from .transport import GazelleTransport
from .resources.artists import ArtistResource
from .resources.collages import CollageResource
from .resources.inbox import InboxResource
from .resources.notifications import NotificationResource
from .resources.requests import RequestResource
from .resources.torrents import TorrentResource
from .resources.user import UserResource

ORPHEUS_BASE_URL = "https://orpheus.network"
REDACTED_BASE_URL = "https://redacted.ch"


class GazelleClient:
    def __init__(self, transport: GazelleTransport) -> None:
        self._transport = transport
        self._torrents: TorrentResource | None = None
        self._artists: ArtistResource | None = None
        self._requests: RequestResource | None = None
        self._collages: CollageResource | None = None
        self._user: UserResource | None = None
        self._inbox: InboxResource | None = None
        self._notifications: NotificationResource | None = None

    @property
    def torrents(self) -> TorrentResource:
        if self._torrents is None:
            self._torrents = TorrentResource(self._transport)
        return self._torrents

    @property
    def artists(self) -> ArtistResource:
        if self._artists is None:
            self._artists = ArtistResource(self._transport)
        return self._artists

    @property
    def requests(self) -> RequestResource:
        if self._requests is None:
            self._requests = RequestResource(self._transport)
        return self._requests

    @property
    def collages(self) -> CollageResource:
        if self._collages is None:
            self._collages = CollageResource(self._transport)
        return self._collages

    @property
    def user(self) -> UserResource:
        if self._user is None:
            self._user = UserResource(self._transport)
        return self._user

    @property
    def inbox(self) -> InboxResource:
        if self._inbox is None:
            self._inbox = InboxResource(self._transport)
        return self._inbox

    @property
    def notifications(self) -> NotificationResource:
        if self._notifications is None:
            self._notifications = NotificationResource(self._transport)
        return self._notifications

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> GazelleClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


class OrpheusClient(GazelleClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            GazelleTransport(ORPHEUS_BASE_URL, username=username, password=password, api_key=api_key, **kwargs)
        )


class RedactedClient(GazelleClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            GazelleTransport(REDACTED_BASE_URL, username=username, password=password, api_key=api_key, **kwargs)
        )
