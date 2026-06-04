import os

import pytest


def _skip_if_missing(*var_names: str) -> None:
    missing = [v for v in var_names if not os.getenv(v)]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")


@pytest.fixture
def orpheus_api_key() -> str:
    _skip_if_missing("ORPHEUS_API_KEY")
    return os.environ["ORPHEUS_API_KEY"]


@pytest.fixture
def orpheus_credentials() -> tuple[str, str]:
    _skip_if_missing("ORPHEUS_USERNAME", "ORPHEUS_PASSWORD")
    return os.environ["ORPHEUS_USERNAME"], os.environ["ORPHEUS_PASSWORD"]


@pytest.fixture
def redacted_api_key() -> str:
    _skip_if_missing("REDACTED_API_KEY")
    return os.environ["REDACTED_API_KEY"]


@pytest.fixture
def redacted_credentials() -> tuple[str, str]:
    _skip_if_missing("REDACTED_USERNAME", "REDACTED_PASSWORD")
    return os.environ["REDACTED_USERNAME"], os.environ["REDACTED_PASSWORD"]


@pytest.fixture
def cross_seed_source_torrent_id() -> int:
    _skip_if_missing("ORPHEUS_API_KEY", "REDACTED_API_KEY", "CROSS_SEED_SOURCE_TORRENT_ID")
    return int(os.environ["CROSS_SEED_SOURCE_TORRENT_ID"])
