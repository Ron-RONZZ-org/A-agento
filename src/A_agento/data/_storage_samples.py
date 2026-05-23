from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from A_agento.data._storage_base import get_db


def add_style_sample(
    uuid: str,
    sample_type: str,
    content: str,
    source_email_uuid: str | None = None,
    metadata: str | None = None,
) -> dict[str, Any]:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """INSERT INTO stiloj (uuid, sample_type, content, source_email_uuid, metadata, created_at, active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (uuid, sample_type, content, source_email_uuid, metadata, now),
    )

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
    db = get_db()
    return db.execute("SELECT * FROM stiloj ORDER BY created_at DESC")


def delete_style_sample(uuid: str) -> None:
    db = get_db()
    db.execute("DELETE FROM stiloj WHERE uuid = ?", (uuid,))
    db.execute("DELETE FROM stiloj_fts WHERE rowid IN (SELECT rowid FROM stiloj WHERE uuid = ?)", (uuid,))


def set_sample_active(uuid: str, active: bool) -> None:
    db = get_db()
    db.execute("UPDATE stiloj SET active = ? WHERE uuid = ?", (1 if active else 0, uuid))


def _sanitize_fts_query(text: str) -> str:
    import re

    tokens = re.findall(r"[a-zA-Z0-9]+", text)
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
    db = get_db()

    fts_query = _sanitize_fts_query(query)
    if not fts_query:
        return []

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
