from pygazelle.client import GazelleClient
from pygazelle.monitoring import TorrentMonitor
from tests.support import MonitorTransport, make_user_torrent_row


def _client(transport: MonitorTransport) -> GazelleClient:
    return GazelleClient(transport)  # type: ignore[arg-type]


async def test_first_poll_establishes_baseline_returns_empty():
    transport = MonitorTransport(
        pages={
            "uploaded": [[make_user_torrent_row(10, 5, "A")]],
            "snatched": [[make_user_torrent_row(20, 6, "B")]],
        }
    )
    monitor = TorrentMonitor(_client(transport))
    assert await monitor.poll() == []


async def test_no_change_poll_returns_empty():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")]], "snatched": [[]]}
    )
    monitor = TorrentMonitor(_client(transport))
    await monitor.poll()  # baseline
    assert await monitor.poll() == []


async def test_deleted_when_group_gone():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        missing_groups=(5,),
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()  # baseline (page with torrent 10)
    events = await monitor.poll()  # torrent 10 gone
    assert [e.kind for e in events] == ["deleted"]
    assert events[0].torrent_id == 10
    assert events[0].group_id == 5
    assert events[0].name == "A"
    assert events[0].replacement_torrent_id is None


async def test_trumped_when_replacement_present():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        groups={5: [11]},  # group 5 still exists, now contains torrent 11 (not 10)
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()
    events = await monitor.poll()
    assert events[0].kind == "trumped"
    assert events[0].replacement_torrent_id == 11


async def test_deleted_when_group_present_but_empty():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        groups={5: []},  # group exists, our torrent gone, nothing replaced it
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()
    events = await monitor.poll()
    assert events[0].kind == "deleted"


async def test_removed_when_list_and_group_disagree():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        groups={5: [10]},
    )
    monitor = TorrentMonitor(_client(transport), page_size=1)
    await monitor.poll()
    events = await monitor.poll()
    assert events[0].kind == "removed"
    assert events[0].replacement_torrent_id is None


async def test_classification_lookups_bounded_by_removals():
    transport = MonitorTransport(
        pages={
            "uploaded": [
                [make_user_torrent_row(10, 5, "A"), make_user_torrent_row(20, 6, "B")],
                [make_user_torrent_row(20, 6, "B")],
            ],
            "snatched": [[]],
        },
        missing_groups=(5,),
    )
    monitor = TorrentMonitor(_client(transport), page_size=2)
    await monitor.poll()
    await monitor.poll()
    assert transport.group_lookups == [5]


import pytest

from pygazelle.errors import GazelleAPIError


async def test_failed_poll_preserves_prior_snapshot():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")]], "snatched": [[]]},
    )
    monitor = TorrentMonitor(_client(transport))
    await monitor.poll()  # baseline OK

    # Make the next user_torrents fetch raise.
    transport._fail_action = ("user_torrents", GazelleAPIError(status_code=500))
    with pytest.raises(GazelleAPIError):
        await monitor.poll()

    # Recover: torrent 10 has since disappeared and its group is gone.
    transport._fail_action = None
    transport._pages = {"uploaded": [[]], "snatched": [[]]}
    transport._missing = {5}
    events = await monitor.poll()
    assert [e.kind for e in events] == ["deleted"]  # change still detected


async def test_source_restriction_watches_only_requested():
    transport = MonitorTransport(
        pages={
            "uploaded": [[make_user_torrent_row(10, 5, "A")]],
            "snatched": [[make_user_torrent_row(20, 6, "B")]],
        }
    )
    monitor = TorrentMonitor(_client(transport), sources=("snatched",))
    await monitor.poll()
    assert monitor._snapshot is not None
    assert set(monitor._snapshot.sources) == {"snatched"}
    assert 20 in monitor._snapshot.sources["snatched"]
