"""Retry helpers for transient SQLite errors."""

from __future__ import annotations

import time

_RETRY_DELAY = 1.0  # seconds


def retry_on_db_locked(fn, *args, **kwargs):
    """Retry *fn* up to 3 times on 'database is locked', 1s apart.

    For 'malformed'/'disk i/o' errors (DB corruption), triggers repair
    immediately and re-raises — the caller must re-acquire the service
    singleton which creates a fresh connection.

    The caller pattern looks like::

        svc = get_service()
        result = retry_on_db_locked(svc.search_fts, query)

    If corruption is detected, ``repair_db()`` resets the cached
    ``_db_instance`` in ``get_db()``, and ``_encik_service`` is set
    to ``None`` so the next ``get_service()`` creates a fresh chain.
    However the *fn* argument is already bound to the old service —
    attempting to retry *fn* after repair would still use the old
    broken connection. Hence we only retry transient locks, not
    corruption.
    """
    last_exc = None
    for attempt in range(3):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            if "malformed" in msg or "disk i/o" in msg:
                # DB corruption: trigger repair and fail fast.
                # Next tool call will re-acquire a fresh connection.
                _trigger_repair()
                raise
            if "database is locked" in msg:
                last_exc = e
                if attempt < 2:
                    time.sleep(_RETRY_DELAY)
                    continue
            raise
    raise last_exc  # type: ignore[misc]


def _trigger_repair() -> None:
    """Close corrupted connection and repair DB, resetting the singleton chain."""
    try:
        from A_encik.data.storage import repair_db
        from A_encik.service import _encik_service

        # Close old SQLiteDB connection, remove cached instance
        repair_db()
        # Next get_service() → get_db() → creates fresh SQLiteDB
        _encik_service = None
    except Exception:
        pass


__all__ = ["retry_on_db_locked", "_trigger_repair"]
