from pygazelle.models.artists import (
    Artist,
    ArtistSimilar,
    ArtistStatistics,
    ArtistTag,
    ArtistTorrentGroup,
    SimilarArtist,
)


def test_artist_model_parses_orpheus_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert isinstance(artist.id, int)
    assert isinstance(artist.name, str)
    # Orpheus returns tag objects with usage counts, not bare strings.
    assert all(isinstance(tag, ArtistTag) for tag in artist.tags)


def test_artist_statistics_parsed_from_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert isinstance(artist.statistics, ArtistStatistics)
    assert artist.statistics.num_groups == 1
    assert artist.statistics.num_snatches == 6
    assert artist.statistics.num_requests == 0


def test_artist_similar_artists_parsed_from_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert len(artist.similar_artists) == 1
    sa = artist.similar_artists[0]
    assert isinstance(sa, ArtistSimilar)
    assert sa.artist_id == 498673
    assert sa.name == "Warder"
    assert sa.score == 200
    assert sa.similar_id == 818849


def test_artist_discography_parsed_from_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert len(artist.discography) == 3
    group = artist.discography[0]
    assert isinstance(group, ArtistTorrentGroup)
    assert group.group_id == 1607112
    assert group.group_name == "Endangered Specie"
    assert group.group_year == 2025
    assert group.group_category_id == 1
    assert group.release_type == 1
    # Orpheus sends discography tags as a {tagId: name} map.
    assert isinstance(group.tags, dict)
    assert group.tags["516"] == "death.metal"
    assert group.artists[0].name == "Dead Point"
    # "torrent" (singular) in the API -> torrents on the model.
    assert len(group.torrents) == 1
    assert group.torrents[0].id == 3637388
    assert group.torrents[0].format == "FLAC"
    assert group.torrents[0].remaster_record_label == "More Hate Productions"
    assert group.torrents[0].has_file is True


def test_artist_profile_extras_parsed_from_fixture(orpheus_artist):
    artist = Artist.model_validate(orpheus_artist)
    assert artist.vanity_house is False
    assert artist.body_bbcode is not None


def test_artist_enrichment_optional_when_absent():
    # A minimal artist response (only id/name) still validates; enrichment
    # fields degrade to empty/None per the tolerant-base-model convention.
    artist = Artist.model_validate({"id": 1, "name": "Solo"})
    assert artist.statistics is None
    assert artist.similar_artists == []
    assert artist.discography == []
    assert artist.vanity_house is None


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
