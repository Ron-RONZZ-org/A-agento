from __future__ import annotations

from typing import Any

from A.data.base import SQLiteDB, backup_db, health_check
from A.core.paths import data_dir
from A.core.backup_targets import BackupTarget

_DB_NAME = "agento"

_SCHEMA: dict[str, str] = {
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
            prioritato INTEGER NOT NULL DEFAULT 0,
            kreita_je TEXT NOT NULL,
            modifita_je TEXT NOT NULL,
            UNIQUE(provider, profile)
        )
    """,
}

_db_instance: SQLiteDB | None = None


def get_db() -> SQLiteDB:
    global _db_instance
    if _db_instance is None:
        db_path = data_dir() / f"{_DB_NAME}.db"
        if not health_check(db_path):
            from A.data.base import repair_db as _repair
            _repair(db_path)
        backup_db(db_path)
        _db_instance = SQLiteDB(db_path, schema=_SCHEMA)
    return _db_instance


def close_db() -> None:
    global _db_instance
    if _db_instance is not None:
        _db_instance = None


def get_backup_targets() -> list[BackupTarget]:
    """Return backup targets for A-agento."""
    return [
        BackupTarget(
            path=data_dir() / f"{_DB_NAME}.db",
            category="data",
            module="agento",
            label="Agento database",
        ),
    ]
