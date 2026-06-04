from pygazelle.client import GazelleClient
from pygazelle.sync import GazelleSyncClient
from tests.support import MonitorTransport, make_user_torrent_row


def test_sync_monitor_poll_returns_without_await():
    transport = MonitorTransport(
        pages={"uploaded": [[make_user_torrent_row(10, 5, "A")], []], "snatched": [[]]},
        missing_groups=(5,),
    )
    sync_client = GazelleSyncClient(GazelleClient(transport))  # pyright: ignore[reportArgumentType]
    try:
        monitor = sync_client.monitor(page_size=1)
        assert monitor.poll() == []  # baseline, no await
        events = monitor.poll()  # torrent 10 gone
        assert [e.kind for e in events] == ["deleted"]
        # Sync (non-coroutine) methods pass through unchanged.
        assert monitor.dump_state() is not None
    finally:
        sync_client.close()
