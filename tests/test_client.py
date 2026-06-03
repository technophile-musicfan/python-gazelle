from typing import Any

import pytest

from pygazelle.errors import GazelleAPIError
from pygazelle.models import (
    Announcements,
    Artist,
    BookmarkedArtist,
    BookmarkedTorrentGroup,
    ForumSubscription,
    Notification,
    SimilarArtist,
    Top10Category,
    Torrent,
    TorrentGroup,
    User,
    UserProfile,
    UserSearchResult,
    UserTorrent,
)
from pygazelle.resources.artists import ArtistResource
from pygazelle.resources.bookmarks import BookmarkResource
from pygazelle.resources.notifications import NotificationResource
from pygazelle.resources.requests import RequestResource
from pygazelle.resources.site import SiteResource
from pygazelle.resources.subscriptions import SubscriptionResource
from pygazelle.resources.torrents import TorrentResource
from pygazelle.resources.user import UserResource


class StubTransport:
    # Values are usually dicts, but some actions (e.g. similar_artists) return a list.
    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses

    async def request(self, action: str, **params) -> Any:
        return self._responses[action]

    async def request_write(
        self,
        action: str,
        *,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, Any] | None = None,
        include_auth_key: bool = True,
    ) -> Any:
        return self._responses[action]

    async def download(self, torrent_id: int) -> bytes:
        return b"fake-torrent-data"


class CapturingTransport(StubTransport):
    """StubTransport that records request()/request_write() call arguments."""

    def __init__(self, responses: dict[str, Any]) -> None:
        super().__init__(responses)
        self.calls: dict[str, Any] = {}
        self.write_calls: list[dict[str, Any]] = []

    async def request(self, action: str, **params) -> Any:
        self.calls.update(params)
        return self._responses[action]

    async def request_write(
        self,
        action: str,
        *,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
        params: dict[str, Any] | None = None,
        include_auth_key: bool = True,
    ) -> Any:
        self.write_calls.append({"action": action, "data": data, "files": files, "params": params})
        return self._responses[action]


def _edition_payload(**overrides) -> dict:
    """A minimal valid action=torrentgroup edition (a Torrent without its group)."""
    base = {
        "id": 100,
        "media": "CD",
        "format": "FLAC",
        "encoding": "Lossless",
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
    }
    return {**base, **overrides}


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


async def test_torrent_resource_get_group_returns_group_with_torrents():
    stub = StubTransport(
        {
            "torrentgroup": {
                "group": {
                    "id": 7,
                    "name": "Album",
                    "year": 2020,
                    "categoryName": "Music",
                    "releaseType": 1,
                    "wikiBody": "<p>notes</p>",
                    "tags": ["rock"],
                    "musicInfo": {"artists": [{"id": 3, "name": "Radiohead"}]},
                },
                "torrents": [
                    _edition_payload(id=100, media="CD", format="FLAC", encoding="Lossless"),
                    _edition_payload(id=101, media="WEB", format="MP3", encoding="320"),
                ],
            }
        }
    )
    resource = TorrentResource(stub)
    group = await resource.get_group(7)
    assert isinstance(group, TorrentGroup)
    assert group.id == 7
    assert group.category_name == "Music"
    # editions are parsed as full Torrent models, sans embedded group
    assert [t.id for t in group.torrents] == [100, 101]
    assert all(isinstance(t, Torrent) for t in group.torrents)
    assert group.torrents[0].format == "FLAC"
    # artists are surfaced from musicInfo, which has no top-level "artists" key
    assert [a.name for a in group.artists] == ["Radiohead"]


async def test_torrent_resource_get_group_raises_on_missing_group():
    stub = StubTransport({"torrentgroup": {"torrents": []}})
    resource = TorrentResource(stub)
    with pytest.raises(GazelleAPIError):
        await resource.get_group(7)


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


async def test_artist_resource_similar_returns_similar_artists():
    # similar_artists returns a bare JSON array as its response value.
    stub = StubTransport(
        {
            "similar_artists": [
                {"id": 8307, "name": "Fairmont", "score": 200},
                {"id": 3693, "name": "Paul Kalkbrenner", "score": 150},
            ]
        }
    )
    resource = ArtistResource(stub)
    similar = await resource.similar(42)
    assert [a.id for a in similar] == [8307, 3693]
    assert all(isinstance(a, SimilarArtist) for a in similar)
    assert similar[0].name == "Fairmont"
    assert similar[0].score == 200


async def test_artist_resource_similar_handles_null_response():
    # An artist with no similar artists can come back as null, not [].
    resource = ArtistResource(StubTransport({"similar_artists": None}))
    assert await resource.similar(42) == []


async def test_artist_resource_similar_passes_limit():
    transport = CapturingTransport({"similar_artists": []})
    result = await ArtistResource(transport).similar(42, limit=5)
    assert result == []
    assert transport.calls == {"id": 42, "limit": 5}


async def test_artist_resource_similar_omits_limit_when_unset():
    transport = CapturingTransport({"similar_artists": []})
    await ArtistResource(transport).similar(42)
    assert transport.calls == {"id": 42}


async def test_user_resource_get_returns_profile():
    stub = StubTransport(
        {
            "user": {
                "username": "alice",
                "avatar": "http://example/a.png",
                "isFriend": False,
                "profileText": "hi",
                "stats": {
                    "joinedDate": "2020-01-01",
                    "lastAccess": "2026-06-01",
                    "uploaded": 1000,
                    "downloaded": 500,
                    "ratio": 2.0,
                    "requiredRatio": 0.6,
                },
                "community": {
                    "uploaded": 5,
                    "groups": 3,
                    "seeding": 10,
                    "leeching": 0,
                    "snatched": 20,
                    "posts": 7,
                },
            }
        }
    )
    profile = await UserResource(stub).get(42)
    assert isinstance(profile, UserProfile)
    # The API omits id; the resource injects the request param.
    assert profile.id == 42
    assert profile.username == "alice"
    assert profile.stats is not None and profile.stats.uploaded == 1000
    assert profile.community is not None and profile.community.seeding == 10


async def test_user_resource_search_returns_results():
    stub = StubTransport(
        {
            "usersearch": {
                "currentPage": 1,
                "pages": 1,
                "results": [
                    {
                        "userId": 5,
                        "username": "bob",
                        "donor": True,
                        "warned": False,
                        "enabled": True,
                        "class": "User",
                    }
                ],
            }
        }
    )
    results = await UserResource(stub).search("bob")
    assert len(results) == 1
    assert isinstance(results[0], UserSearchResult)
    assert results[0].user_id == 5
    # `class` is aliased to user_class.
    assert results[0].user_class == "User"


async def test_user_resource_torrents_reads_type_keyed_list():
    stub = StubTransport(
        {
            "user_torrents": {
                "seeding": [
                    {
                        "groupId": 1,
                        "torrentId": 100,
                        "name": "Album",
                        "torrentSize": 500,
                        "artistId": 3,
                        "artistName": "X",
                    }
                ],
                "total": 1,
            }
        }
    )
    results = await UserResource(stub).torrents(42, type="seeding")
    assert len(results) == 1
    assert isinstance(results[0], UserTorrent)
    assert results[0].torrent_id == 100
    assert results[0].artist_name == "X"


async def test_user_resource_torrents_empty_when_type_absent():
    stub = StubTransport({"user_torrents": {"total": 0}})
    results = await UserResource(stub).torrents(42, type="seeding")
    assert results == []


async def test_user_resource_torrents_passes_params():
    transport = CapturingTransport({"user_torrents": {"uploaded": [], "total": 0}})
    await UserResource(transport).torrents(42, type="uploaded", limit=10, offset=20)
    assert transport.calls == {"id": 42, "type": "uploaded", "limit": 10, "offset": 20}


async def test_bookmark_resource_torrents_returns_groups():
    stub = StubTransport(
        {
            "bookmarks": {
                "bookmarks": [
                    {
                        "id": 1,
                        "name": "Album",
                        "year": 2020,
                        "tagList": "rock",
                        "releaseType": 1,
                        "torrents": [
                            {
                                "id": 100,
                                "groupId": 1,
                                "media": "CD",
                                "format": "FLAC",
                                "encoding": "Lossless",
                                "size": 500,
                                "seeders": 10,
                            }
                        ],
                    }
                ]
            }
        }
    )
    groups = await BookmarkResource(stub).torrents()
    assert len(groups) == 1
    assert isinstance(groups[0], BookmarkedTorrentGroup)
    assert groups[0].id == 1
    assert groups[0].tag_list == "rock"
    assert groups[0].torrents[0].id == 100
    assert groups[0].torrents[0].group_id == 1


async def test_bookmark_resource_torrents_passes_type():
    transport = CapturingTransport({"bookmarks": {"bookmarks": []}})
    await BookmarkResource(transport).torrents()
    assert transport.calls == {"type": "torrents"}


async def test_bookmark_resource_artists_returns_artists():
    stub = StubTransport({"bookmarks": {"artists": [{"artistId": 5, "artistName": "X"}]}})
    artists = await BookmarkResource(stub).artists()
    assert len(artists) == 1
    assert isinstance(artists[0], BookmarkedArtist)
    assert artists[0].artist_id == 5
    assert artists[0].artist_name == "X"


async def test_bookmark_resource_artists_passes_type():
    transport = CapturingTransport({"bookmarks": {"artists": []}})
    await BookmarkResource(transport).artists()
    assert transport.calls == {"type": "artists"}


async def test_subscription_resource_list_returns_threads():
    stub = StubTransport(
        {
            "subscriptions": {
                "threads": [
                    {
                        "forumId": 1,
                        "forumName": "General",
                        "threadId": 10,
                        "threadTitle": "Hi",
                        "postId": 100,
                        "lastPostId": 200,
                        "locked": False,
                        "new": True,
                    }
                ]
            }
        }
    )
    subs = await SubscriptionResource(stub).list()
    assert len(subs) == 1
    assert isinstance(subs[0], ForumSubscription)
    assert subs[0].thread_id == 10
    assert subs[0].forum_name == "General"
    assert subs[0].new is True


async def test_subscription_resource_list_empty_when_absent():
    stub = StubTransport({"subscriptions": {}})
    assert await SubscriptionResource(stub).list() == []


async def test_site_resource_top10_returns_categories():
    # top10 returns a bare JSON array of category objects.
    stub = StubTransport(
        {
            "top10": [
                {
                    "caption": "Most Active Torrents",
                    "tag": "day",
                    "limit": 10,
                    "results": [{"torrentId": 1, "groupName": "Album"}],
                }
            ]
        }
    )
    cats = await SiteResource(stub).top10()
    assert len(cats) == 1
    assert isinstance(cats[0], Top10Category)
    assert cats[0].tag == "day"
    # results are kept as raw dicts (shape varies by type).
    assert cats[0].results[0]["torrentId"] == 1


async def test_site_resource_top10_defaults_to_torrents():
    transport = CapturingTransport({"top10": []})
    await SiteResource(transport).top10()
    assert transport.calls == {"type": "torrents"}


async def test_site_resource_top10_passes_type_and_limit():
    transport = CapturingTransport({"top10": []})
    await SiteResource(transport).top10(type="tags", limit=100)
    assert transport.calls == {"type": "tags", "limit": 100}


async def test_site_resource_announcements_returns_news_and_blog():
    stub = StubTransport(
        {
            "announcements": {
                "announcements": [{"newsId": 1, "title": "Hi", "body": "b", "newsTime": "2026"}],
                "blogPosts": [
                    {"blogId": 2, "title": "Blog", "body": "bb", "blogTime": "2026", "threadId": 9}
                ],
            }
        }
    )
    result = await SiteResource(stub).announcements()
    assert isinstance(result, Announcements)
    assert result.announcements[0].news_id == 1
    assert result.blog_posts[0].blog_id == 2
    assert result.blog_posts[0].thread_id == 9


async def test_site_resource_announcements_empty_defaults():
    stub = StubTransport({"announcements": {}})
    result = await SiteResource(stub).announcements()
    assert result.announcements == []
    assert result.blog_posts == []


async def test_torrent_add_tag_joins_list_and_returns_result():
    transport = CapturingTransport({"add_tag": {"added": ["rock", "metal"], "rejected": []}})
    result = await TorrentResource(transport).add_tag(5, ["rock", "metal"])
    call = transport.write_calls[0]
    assert call["action"] == "add_tag"
    assert call["data"] == {"groupid": 5, "tagname": "rock,metal"}
    assert result.added == ["rock", "metal"]


async def test_torrent_add_tag_accepts_string():
    transport = CapturingTransport({"add_tag": {"added": [], "rejected": ["dupe"]}})
    result = await TorrentResource(transport).add_tag(5, "jazz")
    assert transport.write_calls[0]["data"]["tagname"] == "jazz"
    assert result.rejected == ["dupe"]


async def test_torrent_add_log_sends_id_param_and_logfiles():
    transport = CapturingTransport(
        {
            "add_log": {
                "torrentId": 9,
                "score": 100,
                "checksum": "ok",
                "logcheckerVersion": "1.0",
                "logSummaries": [{"score": 100, "ripper": "EAC"}],
            }
        }
    )
    result = await TorrentResource(transport).add_log(9, b"LOGDATA")
    call = transport.write_calls[0]
    assert call["action"] == "add_log"
    assert call["params"] == {"id": 9}
    # multipart field name is the array key "logfiles[]".
    assert call["files"][0][0] == "logfiles[]"
    assert result.torrent_id == 9
    assert result.log_summaries[0].ripper == "EAC"


async def test_torrent_add_log_accepts_multiple_logs():
    transport = CapturingTransport({"add_log": {"torrentId": 9}})
    await TorrentResource(transport).add_log(9, [b"L1", b"L2"])
    files = transport.write_calls[0]["files"]
    assert len(files) == 2
    assert all(f[0] == "logfiles[]" for f in files)


async def test_request_fill_posts_requestid_and_torrentid():
    transport = CapturingTransport(
        {"request_fill": {"requestId": 3, "torrentId": 7, "fillerName": "me", "bounty": 100}}
    )
    result = await RequestResource(transport).fill(3, torrent_id=7)
    assert transport.write_calls[0]["data"] == {"requestid": 3, "torrentid": 7}
    assert result.filler_name == "me"
    assert result.bounty == 100


async def test_request_fill_accepts_link():
    transport = CapturingTransport({"request_fill": {"requestId": 3}})
    await RequestResource(transport).fill(3, link="https://x/torrents.php?id=7")
    assert transport.write_calls[0]["data"] == {
        "requestid": 3,
        "link": "https://x/torrents.php?id=7",
    }


async def test_request_fill_requires_torrent_or_link():
    transport = CapturingTransport({})
    with pytest.raises(ValueError):
        await RequestResource(transport).fill(3)


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
    assert isinstance(client.bookmarks, BookmarkResource)
    assert isinstance(client.subscriptions, SubscriptionResource)
    assert isinstance(client.site, SiteResource)


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
