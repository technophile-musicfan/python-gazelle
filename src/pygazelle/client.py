from __future__ import annotations

from typing import Unpack

# Runtime-safe: monitoring.py imports GazelleClient only under TYPE_CHECKING, so
# this top-level import does not form a runtime cycle. (basedpyright's static
# reportImportCycles is disabled for this pair — see pyproject.toml.)
from .monitoring import TorrentMonitor
from .resources.artists import ArtistResource
from .resources.bookmarks import BookmarkResource
from .resources.collages import CollageResource
from .resources.inbox import InboxResource
from .resources.notifications import NotificationResource
from .resources.requests import RequestResource
from .resources.site import SiteResource
from .resources.subscriptions import SubscriptionResource
from .resources.torrents import TorrentResource
from .resources.user import UserResource, UserTorrentType
from .transport import GazelleTransport, TransportOptions

ORPHEUS_BASE_URL = "https://orpheus.network"
# RED migrated from redacted.ch to redacted.sh; the old domain returns HTTP 410.
REDACTED_BASE_URL = "https://redacted.sh"

# VERIFY announce hosts against each tracker (NOT the API host).
ORPHEUS_ANNOUNCE_HOST = "home.opsfet.ch"
REDACTED_ANNOUNCE_HOST = "flacsfor.me"


class GazelleClient:
    def __init__(self, transport: GazelleTransport) -> None:
        self._transport: GazelleTransport = transport
        self._torrents: TorrentResource | None = None
        self._artists: ArtistResource | None = None
        self._requests: RequestResource | None = None
        self._collages: CollageResource | None = None
        self._user: UserResource | None = None
        self._inbox: InboxResource | None = None
        self._notifications: NotificationResource | None = None
        self._bookmarks: BookmarkResource | None = None
        self._subscriptions: SubscriptionResource | None = None
        self._site: SiteResource | None = None

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

    @property
    def bookmarks(self) -> BookmarkResource:
        if self._bookmarks is None:
            self._bookmarks = BookmarkResource(self._transport)
        return self._bookmarks

    @property
    def subscriptions(self) -> SubscriptionResource:
        if self._subscriptions is None:
            self._subscriptions = SubscriptionResource(self._transport)
        return self._subscriptions

    @property
    def site(self) -> SiteResource:
        if self._site is None:
            self._site = SiteResource(self._transport)
        return self._site

    def monitor(
        self,
        *,
        sources: tuple[UserTorrentType, ...] = ("uploaded", "snatched"),
        page_size: int = 50,
    ) -> TorrentMonitor:
        """Construct a TorrentMonitor bound to this client."""
        return TorrentMonitor(self, sources=sources, page_size=page_size)

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
        **kwargs: Unpack[TransportOptions],
    ) -> None:
        kwargs.setdefault("announce_host", ORPHEUS_ANNOUNCE_HOST)
        super().__init__(
            GazelleTransport(
                ORPHEUS_BASE_URL, username=username, password=password, api_key=api_key, **kwargs
            )
        )


class RedactedClient(GazelleClient):
    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        **kwargs: Unpack[TransportOptions],
    ) -> None:
        # RED expects the bare API key in the Authorization header (no "token " prefix).
        kwargs.setdefault("api_key_prefix", "")
        kwargs.setdefault("announce_host", REDACTED_ANNOUNCE_HOST)
        super().__init__(
            GazelleTransport(
                REDACTED_BASE_URL, username=username, password=password, api_key=api_key, **kwargs
            )
        )
