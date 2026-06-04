from .client import GazelleClient, OrpheusClient, RedactedClient
from .crossseed import CrossSeedResult, cross_seed, find_candidates, verify_match
from .errors import (
    GazelleAPIError,
    GazelleAuthError,
    GazelleError,
    GazelleNotFoundError,
    GazelleRateLimitError,
)
from .models.monitoring import TorrentChangeEvent
from .monitoring import TorrentMonitor
from .sync import GazelleSyncClient, OrpheusClientSync, RedactedClientSync

__all__ = [
    "GazelleClient",
    "OrpheusClient",
    "RedactedClient",
    "GazelleSyncClient",
    "OrpheusClientSync",
    "RedactedClientSync",
    "GazelleError",
    "GazelleAuthError",
    "GazelleRateLimitError",
    "GazelleNotFoundError",
    "GazelleAPIError",
    "TorrentMonitor",
    "TorrentChangeEvent",
    "cross_seed",
    "find_candidates",
    "verify_match",
    "CrossSeedResult",
]
