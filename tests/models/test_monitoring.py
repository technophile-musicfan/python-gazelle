from pygazelle.models.monitoring import (
    MonitoredTorrent,
    MonitorSnapshot,
    TorrentChangeEvent,
)


def test_change_event_holds_all_fields():
    ev = TorrentChangeEvent(
        kind="trumped",
        source="uploaded",
        torrent_id=10,
        group_id=5,
        name="Some Release",
        replacement_torrent_id=11,
    )
    assert ev.kind == "trumped"
    assert ev.source == "uploaded"
    assert ev.torrent_id == 10
    assert ev.group_id == 5
    assert ev.name == "Some Release"
    assert ev.replacement_torrent_id == 11


def test_change_event_replacement_defaults_none():
    ev = TorrentChangeEvent(kind="deleted", source="snatched", torrent_id=1, group_id=2, name="X")
    assert ev.replacement_torrent_id is None


def test_snapshot_round_trips_through_json():
    snap = MonitorSnapshot(
        sources={
            "uploaded": {10: MonitoredTorrent(torrent_id=10, group_id=5, name="A")},
            "snatched": {20: MonitoredTorrent(torrent_id=20, group_id=6, name="B")},
        }
    )
    dumped = snap.model_dump(mode="json")
    # JSON object keys are strings; the model must coerce them back to ints.
    restored = MonitorSnapshot.model_validate(dumped)
    assert restored == snap
    assert restored.sources["uploaded"][10].name == "A"
