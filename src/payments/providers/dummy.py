from __future__ import annotations

import hmac
import hashlib
import json
from typing import Any
from .base import PaymentProvider
from src.core.config import get_settings


class DummyProvider(PaymentProvider):
    name = "dummy"

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        secret = get_settings().PAYMENT_HMAC_SECRET.encode()
        signature = headers.get("X-Dummy-Signature", "")
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid HMAC signature")
        payload = json.loads(body.decode("utf-8"))
        return payload

