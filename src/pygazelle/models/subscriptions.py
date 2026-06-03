from .base import GazelleModel


class ForumSubscription(GazelleModel):
    """A subscribed forum thread (action=subscriptions)."""

    forum_id: int
    forum_name: str | None = None
    thread_id: int
    thread_title: str | None = None
    post_id: int | None = None
    last_post_id: int | None = None
    locked: bool | None = None
    new: bool | None = None  # unread status
