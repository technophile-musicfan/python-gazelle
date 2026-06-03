from pygazelle.models.artists import Artist, ArtistTag, SimilarArtist


def test_artist_model_parses_orpheus_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert isinstance(artist.id, int)
    assert isinstance(artist.name, str)
    # Orpheus returns tag objects with usage counts, not bare strings.
    assert all(isinstance(tag, ArtistTag) for tag in artist.tags)


def test_similar_artist_model_parses():
    sa = SimilarArtist.model_validate({"id": 8307, "name": "Fairmont", "score": 200})
    assert sa.id == 8307
    assert sa.name == "Fairmont"
    assert sa.score == 200


def test_similar_artist_score_optional():
    sa = SimilarArtist.model_validate({"id": 1, "name": "NoScore"})
    assert sa.score is None


def test_similar_artists_parses_orpheus_fixture(orpheus_similar_artists):
    # The response value is a bare array of {id, name, score}.
    artists = [SimilarArtist.model_validate(a) for a in orpheus_similar_artists]
    assert all(isinstance(a.id, int) and isinstance(a.name, str) for a in artists)
