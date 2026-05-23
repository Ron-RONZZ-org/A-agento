from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from A_agento.data._storage_base import get_db


def add_template(
    uuid: str,
    nomo: str,
    titolo: str,
    enhavo: str,
) -> dict[str, Any]:
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
    db = get_db()
    return db.execute_one(
        "SELECT * FROM sablonoj WHERE nomo = ?", (nomo,)
    )


def list_templates() -> list[dict[str, Any]]:
    db = get_db()
    return db.execute("SELECT * FROM sablonoj ORDER BY nomo")


def update_template(uuid: str, enhavo: str) -> dict[str, Any] | None:
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE sablonoj SET enhavo = ?, modifita_je = ? WHERE uuid = ?",
        (enhavo, now, uuid),
    )
    return get_template_by_uuid(uuid)


def get_template_by_uuid(uuid: str) -> dict[str, Any] | None:
    db = get_db()
    return db.execute_one(
        "SELECT * FROM sablonoj WHERE uuid = ?", (uuid,)
    )


def delete_template(uuid: str) -> None:
    db = get_db()
    db.execute("DELETE FROM sablonoj WHERE uuid = ?", (uuid,))
