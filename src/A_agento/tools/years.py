"""Calendar time entry management for encik knowledge base.

Provides ensure/create cascade: century → decade → year.
Each level sets the previous as superklaso (parent).
"""

from __future__ import annotations

import json

from A_agento.tools._retry import retry_on_db_locked as _retry_on_db_locked


def _ensure_or_create(
    titolo: str,
    terminologio_eo: str,
    difino_eo: str,
    superklaso: list[str] | None = None,
) -> str:
    """Find an entry by title or create it. Returns UUID.

    Args:
        titolo: Entry title
        terminologio_eo: Esperanto term
        difino_eo: Definition in Esperanto
        superklaso: Optional parent UUIDs

    Returns:
        UUID string
    """
    from A_encik.service import get_service

    svc = get_service()
    existing = _retry_on_db_locked(svc.find_by_titolo, titolo)
    if existing:
        return existing["uuid"]

    data = {
        "terminologio": {"eo": terminologio_eo},
        "difinoj": {"eo": difino_eo},
    }
    if superklaso:
        data["superklaso"] = superklaso
    entry = _retry_on_db_locked(svc.create, data)
    return entry["uuid"]


# Fixed UUIDs for calendar time entries (from user's encik DB)
_YEAR_JARO_UUID = "592e5797"
_YEAR_JARDEKO_UUID = "82064f60"
_YEAR_JARCENTO_UUID = "8677ddbd"
_YEAR_GREGORIA_UUID = "caaf64dc"


def _ensure_year_entry(year: str, bce: bool = False) -> str:
    """Create or retrieve calendar time entries for a year.

    Cascading creation: century → decade → year.
    Returns ALL three UUIDs so the LLM can reference the year, its
    decade, or its century as needed.

    Args:
        year: Year string (1-4 digits, e.g. "1879")

    Returns:
        JSON with ``uuid``, ``decade_uuid``, ``century_uuid`` (all 8-char prefixes)
    """
    year_str = year.strip()
    if not year_str.isdigit() or not (1 <= len(year_str) <= 4):
        return json.dumps({"error": f"Invalid year: '{year_str}'. Must be 1-4 digits."})

    try:
        from A_encik.service import get_service

        svc = get_service()
        entry = _retry_on_db_locked(svc.ensure_year, y, bce=bce)

        decade_start = (y // 10) * 10
        century_num = (y - 1) // 100 + 1

        decade_titolo = f"{decade_start}a jardeko{era_long} (kalendara jardeko)"
        decade = _retry_on_db_locked(svc.find_by_titolo, decade_titolo)

        century_titolo = f"{century_num}a jarcento{era_long} (kalendara jarcento)"
        century = _retry_on_db_locked(svc.find_by_titolo, century_titolo)

        result: dict[str, str] = {"uuid": entry["uuid"][:8]}
        if decade:
            result["decade_uuid"] = decade["uuid"][:8]
        if century:
            result["century_uuid"] = century["uuid"][:8]

        return json.dumps(result, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        err_msg = str(e)
        if "database is locked" in err_msg.lower():
            err_msg = f"database is locked (year={year!r})"
        return json.dumps({"error": err_msg})


def _ensure_decade_entry(decade: str, bce: bool = False) -> str:
    """Create or retrieve a decade entry and its parent century.

    Args:
        decade: Decade start year (multiple of 10, e.g. "1780")

    Returns:
        JSON with ``uuid``, ``century_uuid``
    """
    d = decade.strip()
    if not d.isdigit():
        return json.dumps({"error": f"Invalid decade: '{d}'. Must be a number."})
    dv = int(d)
    if dv % 10 != 0:
        return json.dumps(
            {"error": f"Invalid decade: '{d}'. Must be a multiple of 10 (e.g. 1780)."}
        )

    try:
        from A_encik.service import get_service

        svc = get_service()
        entry = _retry_on_db_locked(svc.ensure_decade, dv, bce=bce)
        era_short, era_long = (" a.K.E.", " (a.K.E.)") if bce else ("", "")
        century_num = (dv - 1) // 100 + 1
        century_titolo = f"{century_num}a jarcento{era_long} (kalendara jarcento)"
        century = _retry_on_db_locked(svc.find_by_titolo, century_titolo)
        result: dict[str, str] = {"uuid": entry["uuid"][:8]}
        if century:
            result["century_uuid"] = century["uuid"][:8]
        return json.dumps(result, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        err_msg = str(e)
        if "database is locked" in err_msg.lower():
            err_msg = f"database is locked (decade={decade!r})"
        return json.dumps({"error": err_msg})


def _ensure_century_entry(century: str, bce: bool = False) -> str:
    """Create or retrieve a century entry.

    Args:
        century: Century number (e.g. "18" for the 18th century)

    Returns:
        JSON with ``uuid``
    """
    c = century.strip()
    if not c.isdigit():
        return json.dumps({"error": f"Invalid century: '{c}'. Must be a number."})

    try:
        from A_encik.service import get_service

        svc = get_service()
        entry = _retry_on_db_locked(svc.ensure_century, int(c), bce=bce)
        return json.dumps({"uuid": entry["uuid"][:8]}, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        err_msg = str(e)
        if "database is locked" in err_msg.lower():
            err_msg = f"database is locked (century={century!r})"
        return json.dumps({"error": err_msg})