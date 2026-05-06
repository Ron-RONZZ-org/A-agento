"""SQLite storage for A-agento.

Provides database for agent metadata, prompt templates, and generation history.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from A.data.base import SQLiteDB
from A.core.paths import data_dir

# Database name
_DB_NAME = "agento"

# Schema
_SCHEMA = {
    "historio": """
        CREATE TABLE historio (
            uuid TEXT PRIMARY KEY,
            tipo TEXT NOT NULL,
            prompto TEXT NOT NULL,
            respondon TEXT NOT NULL,
            model TEXT NOT NULL,
            provizanto TEXT NOT NULL,
            kreita_je TEXT NOT NULL
        )
    """,
    "sablonoj": """
        CREATE TABLE sablonoj (
            uuid TEXT PRIMARY KEY,
            nomo TEXT UNIQUE NOT NULL,
            titolo TEXT NOT NULL,
            enhavo TEXT NOT NULL,
            kreita_je TEXT NOT NULL,
            modifita_je TEXT NOT NULL
        )
    """,
    "stiloj": """
        CREATE TABLE stiloj (
            uuid TEXT PRIMARY KEY,
            sample_type TEXT NOT NULL,
            content TEXT NOT NULL,
            source_email_uuid TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """,
    "stiloj_fts": """
        CREATE VIRTUAL TABLE stiloj_fts USING fts5(
            content,
            content='stiloj',
            content_rowid='rowid'
        )
    """,
    "provizanto_agordoj": """
        CREATE TABLE IF NOT EXISTS provizanto_agordoj (
            uuid TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            profile TEXT NOT NULL DEFAULT 'default',
            noto TEXT DEFAULT '',
            modelo TEXT DEFAULT '',
            base_url TEXT DEFAULT '',
            kreita_je TEXT NOT NULL,
            modifita_je TEXT NOT NULL,
            UNIQUE(provider, profile)
        )
    """,
}

_db: SQLiteDB | None = None


def get_db() -> SQLiteDB:
    """Get the SQLite database for A-agento.

    Returns:
        SQLiteDB instance
    """
    global _db
    if _db is None:
        db_path = data_dir() / f"{_DB_NAME}.db"
        _db = SQLiteDB(db_path, schema=_SCHEMA)
    return _db


def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        _db = None


# --- History operations ---


def add_history(
    uuid: str,
    tipo: str,
    prompto: str,
    respondon: str,
    model: str,
    provizanto: str,
) -> dict[str, Any]:
    """Add an LLM generation to history.

    Args:
        uuid: Entry UUID
        tipo: Generation type (resumo, respondo, ago)
        prompto: Input prompt
        respondon: LLM response
        model: Model used
        provizanto: Provider used

    Returns:
        Created entry dict
    """
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    entry = {
        "uuid": uuid,
        "tipo": tipo,
        "prompto": prompto,
        "respondon": respondon,
        "model": model,
        "provizanto": provizanto,
        "kreita_je": now,
    }
    db.execute(
        """INSERT INTO historio 
           (uuid, tipo, prompto, respondon, model, provizanto, kreita_je)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        list(entry.values()),
    )
    return entry


def get_history(uuid: str) -> dict[str, Any] | None:
    """Get a history entry by UUID.

    Args:
        uuid: Entry UUID

    Returns:
        Entry dict or None
    """
    db = get_db()
    return db.execute_one(
        "SELECT * FROM historio WHERE uuid = ?", (uuid,)
    )


def list_history(
    tipo: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List generation history.

    Args:
        tipo: Filter by type (optional)
        limit: Max entries

    Returns:
        List of entries
    """
    db = get_db()
    if tipo:
        return db.execute(
            "SELECT * FROM historio WHERE tipo = ? ORDER BY kreita_je DESC LIMIT ?",
            (tipo, limit),
        )
    return db.execute(
        "SELECT * FROM historio ORDER BY kreita_je DESC LIMIT ?",
        (limit,),
    )


def delete_history(uuid: str) -> None:
    """Delete a history entry.

    Args:
        uuid: Entry UUID
    """
    db = get_db()
    db.execute("DELETE FROM historio WHERE uuid = ?", (uuid,))


def clear_history(days: int = 30) -> int:
    """Clear history older than days.

    Args:
        days: Delete entries older than this many days

    Returns:
        Number of entries deleted
    """
    from datetime import datetime, timedelta, timezone

    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db.execute(
        "DELETE FROM historio WHERE kreita_je < ?",
        (cutoff,),
    )
    # SQLite's changes() returns the number of rows modified by the last statement
    result = db.execute_one("SELECT changes() AS cnt")
    return result["cnt"] if result else 0


# --- Template operations ---


def add_template(
    uuid: str,
    nomo: str,
    titolo: str,
    enhavo: str,
) -> dict[str, Any]:
    """Add a prompt template.

    Args:
        uuid: Entry UUID
        nomo: Template name
        titolo: Display title
        enhavo: Template content

    Returns:
        Created entry dict
    """
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    entry = {
        "uuid": uuid,
        "nomo": nomo,
        "titolo": titolo,
        "enhavo": enhavo,
        "kreita_je": now,
        "modifita_je": now,
    }
    db.execute(
        """INSERT INTO sablonoj 
           (uuid, nomo, titolo, enhavo, kreita_je, modifita_je)
           VALUES (?, ?, ?, ?, ?, ?)""",
        list(entry.values()),
    )
    return entry


def get_template(nomo: str) -> dict[str, Any] | None:
    """Get a template by name.

    Args:
        nomo: Template name

    Returns:
        Template dict or None
    """
    db = get_db()
    return db.execute_one(
        "SELECT * FROM sablonoj WHERE nomo = ?", (nomo,)
    )


def list_templates() -> list[dict[str, Any]]:
    """List all templates.

    Returns:
        List of templates
    """
    db = get_db()
    return db.execute("SELECT * FROM sablonoj ORDER BY nomo")


def update_template(uuid: str, enhavo: str) -> dict[str, Any] | None:
    """Update a template.

    Args:
        uuid: Template UUID
        enhavo: New content

    Returns:
        Updated entry or None
    """
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE sablonoj SET enhavo = ?, modifita_je = ? WHERE uuid = ?",
        (enhavo, now, uuid),
    )
    return get_template_by_uuid(uuid)


def get_template_by_uuid(uuid: str) -> dict[str, Any] | None:
    """Get a template by UUID.

    Args:
        uuid: Template UUID

    Returns:
        Template dict or None
    """
    db = get_db()
    return db.execute_one(
        "SELECT * FROM sablonoj WHERE uuid = ?", (uuid,)
    )


def delete_template(uuid: str) -> None:
    """Delete a template.

    Args:
        uuid: Template UUID
    """
    db = get_db()
    db.execute("DELETE FROM sablonoj WHERE uuid = ?", (uuid,))


# ============================================================================
# Style samples (stiloj) - with FTS5 search
# ============================================================================


def add_style_sample(
    uuid: str,
    sample_type: str,
    content: str,
    source_email_uuid: str | None = None,
    metadata: str | None = None,
) -> dict[str, Any]:
    """Add a style sample.

    Args:
        uuid: Sample UUID
        sample_type: 'reply' or 'summary'
        content: The writing sample text
        source_email_uuid: Source email UUID if applicable
        metadata: JSON string with additional metadata

    Returns:
        Created sample dict
    """
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """INSERT INTO stiloj (uuid, sample_type, content, source_email_uuid, metadata, created_at, active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (uuid, sample_type, content, source_email_uuid, metadata, now),
    )

    # Rebuild FTS index for this sample
    db.execute(
        "INSERT INTO stiloj_fts(rowid, content) SELECT rowid, content FROM stiloj WHERE uuid = ?",
        (uuid,),
    )

    return {
        "uuid": uuid,
        "sample_type": sample_type,
        "content": content,
        "source_email_uuid": source_email_uuid,
        "metadata": metadata,
        "created_at": now,
        "active": 1,
    }


def get_active_samples(sample_type: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Get active style samples.

    Args:
        sample_type: Filter by type ('reply' or 'summary'), or None for all
        limit: Max samples to return

    Returns:
        List of sample dicts
    """
    db = get_db()

    if sample_type:
        return db.execute(
            "SELECT * FROM stiloj WHERE active = 1 AND sample_type = ? ORDER BY created_at DESC LIMIT ?",
            (sample_type, limit),
        )
    return db.execute(
        "SELECT * FROM stiloj WHERE active = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )


def list_style_samples() -> list[dict[str, Any]]:
    """List all style samples.

    Returns:
        List of all sample dicts
    """
    db = get_db()
    return db.execute("SELECT * FROM stiloj ORDER BY created_at DESC")


def delete_style_sample(uuid: str) -> None:
    """Delete a style sample.

    Args:
        uuid: Sample UUID
    """
    db = get_db()
    db.execute("DELETE FROM stiloj WHERE uuid = ?", (uuid,))
    db.execute("DELETE FROM stiloj_fts WHERE rowid IN (SELECT rowid FROM stiloj WHERE uuid = ?)", (uuid,))


def set_sample_active(uuid: str, active: bool) -> None:
    """Set sample active status.

    Args:
        uuid: Sample UUID
        active: True to activate, False to deactivate
    """
    db = get_db()
    db.execute("UPDATE stiloj SET active = ? WHERE uuid = ?", (1 if active else 0, uuid))


def _sanitize_fts_query(text: str) -> str:
    """Sanitize input text for FTS5 MATCH query.

    FTS5 does not support punctuation in queries. This extracts only
    alphanumeric tokens (words) and joins them with OR so partial matches
    still work.

    Args:
        text: Raw input text (e.g. email body)

    Returns:
        Sanitized FTS5 query string
    """
    import re

    tokens = re.findall(r"[a-zA-Z0-9]+", text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        lower = t.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(t)
    if not unique:
        return ""
    return " OR ".join(unique)


def search_similar_samples(query: str, sample_type: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Search style samples using FTS5 for similar content.

    Args:
        query: Search query text (e.g., email body to match against)
        sample_type: Filter by type ('reply' or 'summary'), or None for all
        limit: Max results

    Returns:
        List of matching sample dicts with scores
    """
    db = get_db()

    fts_query = _sanitize_fts_query(query)
    if not fts_query:
        return []

    # Use FTS5 MATCH for similarity search
    if sample_type:
        results = db.execute(
            """SELECT s.*, rank 
               FROM stiloj s 
               JOIN stiloj_fts f ON s.rowid = f.rowid 
               WHERE stiloj_fts MATCH ? AND s.sample_type = ?
               ORDER BY rank 
               LIMIT ?""",
            (fts_query, sample_type, limit),
        )
    else:
        results = db.execute(
            """SELECT s.*, rank 
               FROM stiloj s 
               JOIN stiloj_fts f ON s.rowid = f.rowid 
               WHERE stiloj_fts MATCH ?
               ORDER BY rank 
               LIMIT ?""",
            (fts_query, limit),
        )

    return results


# ============================================================================
# Provider configuration (provizanto_agordoj)
__all__ = [
    "get_db",
    "close_db",
    "add_history",
    "get_history",
    "list_history",
    "delete_history",
    "clear_history",
    "add_template",
    "get_template",
    "list_templates",
    "update_template",
    "delete_template",
    # Style samples (stiloj)
    "add_style_sample",
    "get_active_samples",
    "list_style_samples",
    "delete_style_sample",
    "set_sample_active",
    "search_similar_samples",
]