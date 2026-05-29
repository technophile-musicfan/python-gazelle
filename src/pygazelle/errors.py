class GazelleError(Exception):
    pass


class GazelleAuthError(GazelleError):
    pass


class GazelleRateLimitError(GazelleError):
    pass


class GazelleNotFoundError(GazelleError):
    pass


class GazelleAPIError(GazelleError):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")
