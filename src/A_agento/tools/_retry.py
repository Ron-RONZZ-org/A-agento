"""Retry helper for transient 'database is locked' errors."""

from __future__ import annotations

import time

_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds


def retry_on_db_locked(fn, *args, **kwargs):
    """Retry *fn* if it raises 'database is locked' — up to 3 attempts, 1s apart."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "database is locked" in str(e).lower():
                last_exc = e
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY)
                    continue
            raise
    raise last_exc  # type: ignore[misc]


__all__ = ["retry_on_db_locked"]
