import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(tracker: str, name: str) -> dict:
    path = FIXTURE_DIR / tracker / f"{name}.json"
    if not path.exists():
        pytest.skip(f"Fixture {tracker}/{name}.json not captured yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["response"]


@pytest.fixture
def orpheus_torrent():
    return load_fixture("orpheus", "torrent")


@pytest.fixture
def redacted_torrent():
    return load_fixture("redacted", "torrent")


@pytest.fixture
def orpheus_torrentgroup():
    return load_fixture("orpheus", "torrentgroup")


@pytest.fixture
def redacted_torrentgroup():
    return load_fixture("redacted", "torrentgroup")


@pytest.fixture
def orpheus_artist():
    return load_fixture("orpheus", "artist")


@pytest.fixture
def orpheus_similar_artists():
    return load_fixture("orpheus", "similar_artists")


@pytest.fixture
def orpheus_index():
    return load_fixture("orpheus", "index")


@pytest.fixture
def redacted_index():
    return load_fixture("redacted", "index")


@pytest.fixture
def orpheus_notifications():
    return load_fixture("orpheus", "notifications")


@pytest.fixture
def orpheus_browse():
    return load_fixture("orpheus", "browse")


@pytest.fixture
def redacted_browse():
    return load_fixture("redacted", "browse")
