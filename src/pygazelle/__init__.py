from .client import GazelleClient, OrpheusClient, RedactedClient
from .crossseed import CrossSeedResult, cross_seed, find_candidates, verify_match
from .crossupload import (
    DuplicateMatch,
    UploadDraft,
    UploadResult,
    duplicate_check,
    map_metadata,
    prepare_upload,
    submit_upload,
)
from .errors import (
    GazelleAPIError,
    GazelleAuthError,
    GazelleError,
    GazelleNotFoundError,
    GazelleRateLimitError,
)
from .models.monitoring import TorrentChangeEvent
from .monitoring import TorrentMonitor
from .sync import (
    GazelleSyncClient,
    OrpheusClientSync,
    RedactedClientSync,
    cross_seed_sync,
    prepare_upload_sync,
    submit_upload_sync,
)

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
    "cross_seed_sync",
    "DuplicateMatch",
    "UploadDraft",
    "UploadResult",
    "duplicate_check",
    "map_metadata",
    "prepare_upload",
    "submit_upload",
    "prepare_upload_sync",
    "submit_upload_sync",
]
