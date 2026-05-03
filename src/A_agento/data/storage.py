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
    from datetime import datetime, timezone

    db = get_db()
    cutoff = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        "DELETE FROM historio WHERE kreita_je < datetime(?, ?)",
        (cutoff, f"-{days} days"),
    )
    return cursor.rowcount if cursor else 0


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
]