from __future__ import annotations

import os

from pygazelle.client import OrpheusClient, RedactedClient
from pygazelle.crossseed import cross_seed


async def test_cross_seed_live_read_only(cross_seed_source_torrent_id: int) -> None:
    async with (
        OrpheusClient(api_key=os.environ["ORPHEUS_API_KEY"], max_retries=0) as source,
        RedactedClient(api_key=os.environ["REDACTED_API_KEY"], max_retries=0) as target,
    ):
        result = await cross_seed(source, cross_seed_source_torrent_id, target, max_deep_checks=3)
        assert result is None or result.confidence == "exact"
