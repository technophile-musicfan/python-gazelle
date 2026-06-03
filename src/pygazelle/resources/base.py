from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..transport import SupportsTransport


class BaseResource:
    def __init__(self, transport: SupportsTransport) -> None:
        self._transport: SupportsTransport = transport

    @staticmethod
    def _params(**kwargs: str | int | None) -> dict[str, str | int]:
        """Build a request param dict, dropping any entry whose value is None."""
        return {key: value for key, value in kwargs.items() if value is not None}
