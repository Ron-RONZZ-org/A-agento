"""Encik search and Wikidata property lookup for LLM tool calling."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _try_repair_db() -> None:
    """Attempt DB repair once per session. Safe to call speculatively."""
    if getattr(_try_repair_db, "_done", False):
        return
    _try_repair_db._done = True
    try:
        from A_encik.data.storage import repair_db
        repair_db()
    except Exception:
        pass


def _search_fts(db, query: str, fts_cfg) -> list[dict] | None:
    """Search encik DB using FTS5 for relevance-ranked results.

    Args:
        db: SQLiteDB instance
        query: Search query string
        fts_cfg: FTSConfig from A_encik

    Returns:
        List of matching entries or None if FTS fails
    """
    import re as _re

    try:
        terms = _re.findall(r"[a-zA-Z0-9]+", query)
        if not terms:
            return None
        fts_query = " OR ".join(f"{t}*" for t in terms[:5])

        sql = (
            f"SELECT e.uuid, e.titolo, substr(e.difinio, 1, 200) as preview "
            f"FROM encik e "
            f"JOIN {fts_cfg.fts_table} f ON e.rowid = f.rowid "
            f"WHERE {fts_cfg.fts_table} MATCH ? "
            f"ORDER BY rank "
            f"LIMIT 8"
        )
        return db.execute(sql, (fts_query,))
    except Exception:
        return None


def _search_encik(query: str) -> str:
    """Search encik DB by keyword/title.

    Uses FTS5 for relevance-ranked results when available, falls back to
    LIKE search. If the query is a 4-digit year, short-circuits to
    auto-create the year entry without hitting DB search.

    Args:
        query: Search query string

    Returns:
        JSON with matching entries (title, uuid, preview)
    """
    try:
        clean = query.strip()
        year = _parse_year(clean)
        if year is not None:
            bce = _is_bce(clean)
            return _ensure_year_entry(str(year), bce=bce)

        from A_encik.data.storage import get_db as encik_db
        from A_encik.data.storage import ENCIK_FTS_CONFIG as fts_cfg

        db = encik_db()
        results = _search_fts(db, query, fts_cfg)
        if not results:
            results = db.execute(
                """SELECT uuid, titolo, substr(difinio, 1, 200) as preview
                   FROM encik WHERE titolo LIKE ? OR difinio LIKE ?
                   ORDER BY CASE WHEN titolo LIKE ? THEN 0 ELSE 1 END, titolo
                   LIMIT 8""",
                (f"%{query}%", f"%{query}%", f"{query}%"),
            )
        if results:
            return json.dumps(results, ensure_ascii=False, default=str)

        return json.dumps({"message": f"No entries found for '{query}'"})
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except sqlite3.DatabaseError as e:
        from A import warning as _warn
        _warn(f"Encik DB unavailable: {e}")
        _try_repair_db()
        return json.dumps({"message": f"Search temporarily unavailable: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _get_encik_entry(uuid: str) -> str:
    """Get a full encik entry by UUID.

    Args:
        uuid: Entry UUID (full or prefix)

    Returns:
        JSON with the full entry
    """
    try:
        from A_encik.data.storage import get_db as encik_db
        from A_encik.data.storage import row_to_dict
        from A_encik.enc_format import entry_to_enc

        db = encik_db()
        entry = db.execute_one(
            "SELECT * FROM encik WHERE uuid LIKE ?", (f"{uuid}%",)
        )
        if entry:
            entry_dict = row_to_dict(entry)
            enc_text = entry_to_enc(entry_dict)
            result = {
                "uuid": entry_dict["uuid"],
                "titolo": entry_dict["titolo"],
                "enc_format": enc_text[:2000],
            }
            return json.dumps(result, ensure_ascii=False, default=str)
        return json.dumps({"error": f"No entry found for UUID '{uuid}'"})
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except sqlite3.DatabaseError as e:
        _try_repair_db()
        return json.dumps({"error": f"Entry lookup unavailable: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _lookup_wikidata_property(query: str) -> str:
    """Search for Wikidata properties by English keyword.

    Always queries in English for consistency. Delegates to A-encik's
    semantika_cache which handles: SQLite cache → CSV files → Wikidata API.

    Args:
        query: English keyword (e.g. "profession", "date of birth")

    Returns:
        JSON with results array or error message
    """
    if not query or not query.strip():
        return json.dumps({"results": [], "message": "Empty query"})

    try:
        from A_encik.data.semantika_cache import lookup_property

        result = lookup_property(query.strip())
        return json.dumps(result, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Year helpers (shared between search.py and years.py) ─────────────


def _parse_year(text: str) -> int | None:
    """Parse a year string into a positive integer. Returns None if not valid."""
    t = text.strip()
    for suffix in ("bce", "bc", "a.k.e.", "a.k.", "a.K.E.", "a.K."):
        if t.lower().endswith(suffix.lower()):
            t = t[: -len(suffix)].strip()
            break
    if t.isdigit() and 1 <= len(t) <= 4:
        return int(t)
    return None


def _is_bce(text: str) -> bool:
    """Check if the text indicates a BCE year."""
    t = text.strip().lower()
    return any(
        t.endswith(s) for s in ("bce", "bc", "a.k.e.", "a.k.", "a.k.e", "a.k")
    )


# Import year management functions (avoid circular import)
from A_agento.tools.years import (  # noqa: E402, F401
    _ensure_year_entry,
    _ensure_decade_entry,
    _ensure_century_entry,
)
