from pygazelle.models.user import (
    User,
    UserProfile,
    UserSearchResult,
    UserTorrent,
)


def test_user_model_parses_orpheus_index(orpheus_index):
    user = User.model_validate(orpheus_index)
    assert isinstance(user.id, int)
    assert isinstance(user.username, str)


def test_user_profile_parses_with_injected_id():
    profile = UserProfile.model_validate(
        {
            "id": 42,
            "username": "alice",
            "stats": {"uploaded": 1000, "ratio": 2.0},
            "community": {"seeding": 10},
        }
    )
    assert profile.id == 42
    assert profile.stats is not None and profile.stats.uploaded == 1000
    assert profile.community is not None and profile.community.seeding == 10


def test_user_search_result_aliases_class_keyword():
    result = UserSearchResult.model_validate({"userId": 5, "username": "bob", "class": "Elite"})
    assert result.user_id == 5
    assert result.user_class == "Elite"


def test_user_torrent_parses():
    t = UserTorrent.model_validate(
        {"groupId": 1, "torrentId": 100, "name": "Album", "torrentSize": 500}
    )
    assert t.torrent_id == 100
    assert t.torrent_size == 500
    assert t.artist_name is None
