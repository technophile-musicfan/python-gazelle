from .base import GazelleModel


class Notification(GazelleModel):
    torrent_id: int
    torrent_group_id: int
    group_name: str
    format: str = ""
    notification_type: str = ""
