from pygazelle.models.user import (
    User,
    UserProfile,
    UserSearchResult,
    UserStats,
    UserTorrent,
)


def test_user_model_parses_orpheus_index(orpheus_index):
    user = User.model_validate(orpheus_index)
    assert isinstance(user.id, int)
    assert isinstance(user.username, str)


def test_userstats_parses_orpheus_freeleech_tokens(orpheus_index):
    # Orpheus's index userstats carries freeleech tokens + bonus point info.
    user = User.model_validate(orpheus_index)
    assert user.userstats is not None
    assert user.userstats.tokens == 5
    assert user.userstats.bonus_points == 394721
    assert user.userstats.bonus_points_per_hour == 29.25
    assert user.userstats.user_class == "Elite"


def test_userstats_tolerates_red_index_without_tokens(redacted_index):
    # RED's index userstats omits tokens/bonusPoints — they must stay None.
    user = User.model_validate(redacted_index)
    assert user.userstats is not None
    assert user.userstats.tokens is None
    assert user.userstats.bonus_points is None
    assert user.userstats.bonus_points_per_hour is None
    assert user.userstats.user_class == "Power User"


def test_userstats_token_fields_default_none_without_fixtures():
    # Fixture-free guard so the divergence is covered in CI (fixtures are gitignored):
    # Orpheus-shaped block exposes tokens; RED-shaped block degrades to None.
    orpheus = UserStats.model_validate(
        {
            "uploaded": 1,
            "downloaded": 2,
            "ratio": 0.5,
            "tokens": 5,
            "bonusPoints": 100,
            "bonusPointsPerHour": 1.5,
            "class": "Elite",
        }
    )
    assert orpheus.tokens == 5
    assert orpheus.bonus_points == 100
    assert orpheus.bonus_points_per_hour == 1.5
    assert orpheus.user_class == "Elite"

    red = UserStats.model_validate(
        {"uploaded": 1, "downloaded": 2, "ratio": 9, "class": "Power User"}
    )
    assert red.tokens is None
    assert red.bonus_points is None
    assert red.bonus_points_per_hour is None
    assert red.user_class == "Power User"


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
