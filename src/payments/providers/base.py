from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def parse_webhook(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:  # pragma: no cover - interface
        ...

