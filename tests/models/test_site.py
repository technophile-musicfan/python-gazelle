from pygazelle.models.site import Announcement, Announcements, BlogPost, Top10Category


def test_announcement_aliases():
    a = Announcement.model_validate({"newsId": 1, "title": "T", "body": "B", "newsTime": "2026"})
    assert a.news_id == 1
    assert a.news_time == "2026"


def test_blog_post_aliases():
    b = BlogPost.model_validate({"blogId": 2, "title": "T", "blogTime": "2026", "threadId": 9})
    assert b.blog_id == 2
    assert b.thread_id == 9


def test_announcements_container_defaults_empty():
    a = Announcements.model_validate({})
    assert a.announcements == []
    assert a.blog_posts == []


def test_top10_category_keeps_raw_results():
    c = Top10Category.model_validate(
        {"caption": "X", "tag": "day", "limit": 10, "results": [{"torrentId": 1}]}
    )
    assert c.tag == "day"
    assert c.results[0]["torrentId"] == 1
