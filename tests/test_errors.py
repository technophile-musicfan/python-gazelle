from pygazelle.errors import (
    GazelleAPIError,
    GazelleAuthError,
    GazelleError,
    GazelleNotFoundError,
    GazelleRateLimitError,
)


def test_all_errors_are_gazelle_errors():
    assert issubclass(GazelleAuthError, GazelleError)
    assert issubclass(GazelleRateLimitError, GazelleError)
    assert issubclass(GazelleNotFoundError, GazelleError)
    assert issubclass(GazelleAPIError, GazelleError)


def test_api_error_stores_status_code():
    err = GazelleAPIError(status_code=500, message="server error")
    assert err.status_code == 500


def test_api_error_message_includes_status_code():
    err = GazelleAPIError(status_code=500, message="server error")
    assert "500" in str(err)


def test_gazelle_error_is_exception():
    assert issubclass(GazelleError, Exception)
