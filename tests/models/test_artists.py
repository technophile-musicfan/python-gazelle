from pygazelle.models.artists import Artist, ArtistTag


def test_artist_model_parses_orpheus_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert isinstance(artist.id, int)
    assert isinstance(artist.name, str)
    # Orpheus returns tag objects with usage counts, not bare strings.
    assert all(isinstance(tag, ArtistTag) for tag in artist.tags)
