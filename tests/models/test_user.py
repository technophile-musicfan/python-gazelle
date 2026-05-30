from pygazelle.models.user import User


def test_user_model_parses_orpheus_index(orpheus_index):
    user = User.model_validate(orpheus_index)
    assert isinstance(user.id, int)
    assert isinstance(user.username, str)
