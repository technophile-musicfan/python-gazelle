from pygazelle.models.subscriptions import ForumSubscription


def test_forum_subscription_aliases():
    sub = ForumSubscription.model_validate(
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
    )
    assert sub.forum_id == 1
    assert sub.thread_id == 10
    assert sub.last_post_id == 200
    assert sub.new is True


def test_forum_subscription_optional_fields_default_none():
    sub = ForumSubscription.model_validate({"forumId": 1, "threadId": 10})
    assert sub.forum_name is None
    assert sub.new is None
