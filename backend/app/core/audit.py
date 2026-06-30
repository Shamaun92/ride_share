"""Structured audit logging.

Security- and money-relevant events (auth, settlement, refunds, admin actions)
are emitted as single structured log lines on the dedicated `audit` logger, so
they can be shipped to a SIEM / immutable store separately from app logs.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("audit")


def audit(event: str, **fields: Any) -> None:
    payload = {"event": event, **{k: _coerce(v) for k, v in fields.items()}}
    logger.info(json.dumps(payload, sort_keys=True, default=str))


def _coerce(value: Any) -> Any:
    # UUIDs, enums, datetimes -> strings for stable JSON.
    if hasattr(value, "value") and not isinstance(value, (int, float, bool)):
        return getattr(value, "value")
    return value
