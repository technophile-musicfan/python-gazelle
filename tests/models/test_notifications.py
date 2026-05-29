from pygazelle.models.notifications import Notification


def test_notifications_model_parses_orpheus_fixture(orpheus_notifications):
    results = orpheus_notifications.get("results", [])
    if not results:
        return  # no notifications — skip silently
    notification = Notification.model_validate(results[0])
    assert isinstance(notification.torrent_id, int)
