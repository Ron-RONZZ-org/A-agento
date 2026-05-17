"""Encik search and Wikidata property lookup for LLM tool calling.

Uses A-encik's service layer (EncikService) instead of direct DB access.
"""

from __future__ import annotations

import json
from typing import Any


def _search_encik(query: str) -> str:
    """Search encik DB by keyword/title via EncikService.

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

        from A_encik.service import get_service

        svc = get_service()

        # FTS5 relevance-ranked search, fallback to LIKE
        entries = svc.search_fts(query, limit=8)
        if not entries:
            entries = svc.search_like(query, limit=8)
        if entries:
            results = [
                {
                    "uuid": e.get("uuid", "")[:8],
                    "titolo": e.get("titolo", ""),
                    "preview": (e.get("difinio") or "")[:200],
                }
                for e in entries
            ]
            return json.dumps(results, ensure_ascii=False, default=str)

        return json.dumps({"message": f"No entries found for '{query}'"})
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _get_encik_entry(uuid: str) -> str:
    """Get a full encik entry by UUID via EncikService.

    Args:
        uuid: Entry UUID (full or prefix)

    Returns:
        JSON with the full entry
    """
    try:
        from A_encik.service import get_service
        from A_encik.enc_format import entry_to_enc

        svc = get_service()
        entry = svc.get(uuid)
        if entry:
            enc_text = entry_to_enc(entry)
            result = {
                "uuid": entry["uuid"][:8],
                "titolo": entry.get("titolo", ""),
                "enc_format": enc_text[:2000],
            }
            return json.dumps(result, ensure_ascii=False, default=str)
        return json.dumps({"error": f"No entry found for UUID '{uuid}'"})
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _lookup_wikidata_property(query: str) -> str:
    """Search for Wikidata properties by English keyword.

    Always queries in English for consistency. Delegates to A-encik's
    semantika_cache which handles: SQLite cache -> CSV files -> Wikidata API.

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
