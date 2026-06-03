from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from ..models.base import GazelleModel

if TYPE_CHECKING:
    from ..transport import SupportsTransport

_M = TypeVar("_M", bound=GazelleModel)


class BaseResource:
    def __init__(self, transport: SupportsTransport) -> None:
        self._transport: SupportsTransport = transport

    @staticmethod
    def _params(**kwargs: str | int | None) -> dict[str, str | int]:
        """Build a request param dict, dropping any entry whose value is None."""
        return {key: value for key, value in kwargs.items() if value is not None}

    @staticmethod
    def _parse_list(items: Any, model: type[_M]) -> list[_M]:
        """Validate each element of a (possibly null/absent) list into ``model``."""
        rows: list[Any] = items or []
        return [model.model_validate(row) for row in rows]
