from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..transport import SupportsTransport


class BaseResource:
    def __init__(self, transport: SupportsTransport) -> None:
        self._transport: SupportsTransport = transport
