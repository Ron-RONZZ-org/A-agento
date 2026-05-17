"""Retry helper for transient 'database is locked' errors."""

from __future__ import annotations

import time

_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds


def retry_on_db_locked(fn, *args, **kwargs):
    """Retry *fn* if it raises 'database is locked' or DB corruption — up to 3 attempts, 1s apart."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            if "database is locked" in msg or "malformed" in msg or "disk i/o" in msg:
                last_exc = e
                if attempt < _MAX_RETRIES - 1:
                    # Trigger DB repair on corruption before retry
                    if "malformed" in msg or "disk i/o" in msg:
                        try:
                            from A_encik.data.storage import repair_db
                            from A_encik.service import _encik_service
                            repair_db()
                            _encik_service = None
                        except Exception:
                            pass
                    time.sleep(_RETRY_DELAY)
                    continue
            raise
    raise last_exc  # type: ignore[misc]


__all__ = ["retry_on_db_locked"]
