from typing import Any

from .base import GazelleModel


class Top10Category(GazelleModel):
    """One ranked list from action=top10 (e.g. "Most Active Torrents...").

    The `results` items differ by request type (torrents/tags/users), so they
    are kept as raw dicts rather than a single typed model.
    """

    caption: str | None = None
    tag: str | None = None  # the ranking bucket, e.g. "day", "week", "overall"
    limit: int | None = None
    results: list[dict[str, Any]] = []


class Announcement(GazelleModel):
    news_id: int | None = None
    title: str | None = None
    body: str | None = None
    news_time: str | None = None


class BlogPost(GazelleModel):
    blog_id: int | None = None
    title: str | None = None
    body: str | None = None
    blog_time: str | None = None
    thread_id: int | None = None


class Announcements(GazelleModel):
    """The action=announcements response: site news plus blog posts."""

    announcements: list[Announcement] = []
    blog_posts: list[BlogPost] = []
