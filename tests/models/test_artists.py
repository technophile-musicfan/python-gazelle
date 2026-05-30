import pytest

from pygazelle.models.artists import Artist


@pytest.mark.xfail(
    strict=True,
    reason="python-gazelle-6ue: Orpheus 'tags' is a list of dicts "
    "({name, count}), but Artist.tags is typed list[str].",
)
def test_artist_model_parses_orpheus_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert isinstance(artist.id, int)
    assert isinstance(artist.name, str)
