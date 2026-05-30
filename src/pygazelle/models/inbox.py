from .base import GazelleModel


class Message(GazelleModel):
    conversation_id: int
    subject: str
    sender_id: int
    sender_name: str
    sent_date: str
    sticky: bool = False
    unread: bool = False
