from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

from ..models import Ad, SearchSpec


class BaseScraper(ABC):
    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    def search(self, spec: SearchSpec) -> AsyncIterator[Ad]: ...
