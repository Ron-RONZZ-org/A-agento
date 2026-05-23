from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from A_agento.data._storage_base import get_db


def add_history(
    uuid: str,
    tipo: str,
    prompto: str,
    respondon: str,
    model: str,
    provizanto: str,
) -> dict[str, Any]:
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
    db = get_db()
    return db.execute_one(
        "SELECT * FROM historio WHERE uuid = ?", (uuid,)
    )


def list_history(
    tipo: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
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
    db = get_db()
    db.execute("DELETE FROM historio WHERE uuid = ?", (uuid,))


def clear_history(days: int = 30) -> int:
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db.execute(
        "DELETE FROM historio WHERE kreita_je < ?",
        (cutoff,),
    )
    result = db.execute_one("SELECT changes() AS cnt")
    return result["cnt"] if result else 0
