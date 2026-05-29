from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..transport import GazelleTransport


class BaseResource:
    def __init__(self, transport: GazelleTransport) -> None:
        self._transport = transport
