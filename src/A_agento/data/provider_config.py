"""Provider configuration storage for A-agento.

Stores non-secret provider metadata (label, model, base URL).
API keys are stored separately in the system keyring.
"""

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from A_agento.data.storage import get_db

# Schema for the provider config table
PROVIDER_CONFIG_TABLE = "provizanto_agordoj"

PROVIDER_CONFIG_SCHEMA = {
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


def _ensure_uuid_column() -> None:
    """Add uuid column to existing tables that lack it (migration)."""
    db = get_db()
    cols = db.execute("PRAGMA table_info(provizanto_agordoj)")
    col_names = {c["name"] for c in cols}
    if "uuid" not in col_names:
        db.execute("ALTER TABLE provizanto_agordoj ADD COLUMN uuid TEXT")
        # Backfill UUIDs for existing rows
        rows = db.execute("SELECT rowid FROM provizanto_agordoj WHERE uuid IS NULL")
        for row in rows:
            new_uuid = str(uuid_mod.uuid4())
            db.execute("UPDATE provizanto_agordoj SET uuid = ? WHERE rowid = ?", (new_uuid, row["rowid"]))


# Run migration on import
_ensure_uuid_column()


def save_provider_config(
    provider: str,
    profile: str = "default",
    noto: str = "",
    modelo: str = "",
    base_url: str = "",
) -> dict[str, Any]:
    """Save or update provider configuration metadata.

    Stores non-secret provider metadata (label, model, base URL).
    API keys are stored separately in the system keyring.

    Args:
        provider: Provider name (huggingface, deepseek, openai)
        profile: Profile/label for the key (default: "default")
        noto: User-friendly label
        modelo: Model name override
        base_url: Custom API base URL

    Returns:
        Saved config dict
    """
    from datetime import datetime, timezone

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    existing = get_provider_config(provider, profile)
    if existing:
        db.execute(
            """UPDATE provizanto_agordoj
               SET noto = ?, modelo = ?, base_url = ?, modifita_je = ?
               WHERE uuid = ?""",
            (noto, modelo, base_url, now, existing["uuid"]),
        )
        result = {**existing, "noto": noto, "modelo": modelo, "base_url": base_url}
    else:
        entry_uuid = str(uuid_mod.uuid4())
        db.execute(
            """INSERT INTO provizanto_agordoj
               (uuid, provider, profile, noto, modelo, base_url, kreita_je, modifita_je)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_uuid, provider, profile, noto, modelo, base_url, now, now),
        )
        result = {
            "uuid": entry_uuid,
            "provider": provider,
            "profile": profile,
            "noto": noto,
            "modelo": modelo,
            "base_url": base_url,
        }

    return result


def get_provider_config(
    provider: str,
    profile: str = "default",
) -> dict[str, Any] | None:
    """Get provider configuration by provider and profile.

    Args:
        provider: Provider name
        profile: Profile/label

    Returns:
        Config dict or None
    """
    db = get_db()
    return db.execute_one(
        "SELECT * FROM provizanto_agordoj WHERE provider = ? AND profile = ?",
        (provider, profile),
    )


def get_provider_config_by_uuid(uuid: str) -> dict[str, Any] | None:
    """Get provider configuration by UUID (supports prefix).

    Args:
        uuid: Entry UUID or prefix (e.g. "a1b2c3d4")

    Returns:
        Config dict or None. If prefix matches multiple, returns the first.
    """
    db = get_db()
    return db.execute_one(
        "SELECT * FROM provizanto_agordoj WHERE uuid LIKE ?",
        (f"{uuid}%",),
    )


def list_provider_configs() -> list[dict[str, Any]]:
    """List all provider configurations.

    Returns:
        List of config dicts ordered by provider, profile
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM provizanto_agordoj ORDER BY provider, profile"
    )


def delete_provider_config(
    provider: str | None = None,
    profile: str = "default",
    uuid: str | None = None,
) -> bool:
    """Delete a provider configuration.

    Deletes by UUID if provided, otherwise by provider+profile.
    Note: this does NOT remove the API key from the keyring.
    Use A.core.ai.save_api_key('', provider) to clear the key.

    Args:
        provider: Provider name (required if uuid not given)
        profile: Profile/label (default: "default")
        uuid: Entry UUID (alternative to provider+profile)

    Returns:
        True if deleted, False if not found
    """
    db = get_db()
    if uuid:
        existing = db.execute_one(
            "SELECT 1 FROM provizanto_agordoj WHERE uuid = ?", (uuid,)
        )
        if existing is None:
            return False
        db.execute("DELETE FROM provizanto_agordoj WHERE uuid = ?", (uuid,))
        return True
    else:
        existing = db.execute_one(
            "SELECT 1 FROM provizanto_agordoj WHERE provider = ? AND profile = ?",
            (provider, profile),
        )
        if existing is None:
            return False
        db.execute(
            "DELETE FROM provizanto_agordoj WHERE provider = ? AND profile = ?",
            (provider, profile),
        )
        return True


__all__ = [
    "PROVIDER_CONFIG_SCHEMA",
    "save_provider_config",
    "get_provider_config",
    "get_provider_config_by_uuid",
    "list_provider_configs",
    "delete_provider_config",
    "parse_ref",
    "find_config",
]

# ── Reference parsing (shared between agordo_crud and commands) ─────────────


def parse_ref(ref: str) -> tuple[str | None, str | None, str | None]:
    """Parse a provider reference into (uuid, provider, profile).

    Accepts UUID (full or 8+ hex prefix), provider:profile, or bare provider name.

    A reference is treated as UUID if it contains hex digits only (or hex with
    hyphens) and is at least 8 characters long.
    """
    stripped = ref.strip()
    # Full UUID with hyphens
    if len(stripped) == 36 and stripped.count("-") == 4:
        return (stripped, None, None)
    # UUID prefix or full hex UUID (8-32 chars, all hex)
    if len(stripped) >= 8 and len(stripped) <= 32 and all(c in "0123456789abcdef" for c in stripped.lower()):
        return (stripped, None, None)
    # Provider:profile syntax
    if ":" in stripped:
        parts = stripped.split(":", 1)
        return (None, parts[0], parts[1])
    # Bare provider name
    return (None, stripped, None)


def find_config(ref: str) -> dict | None:
    """Find a provider config by UUID, provider, or provider:profile.

    If the ref looks like a UUID but no config matches, falls back to
    looking it up as a provider name. This handles provider names that
    happen to look like hex strings (e.g. "deadbeef" or "a1b2c3d4").
    """
    uuid, provider, profile = parse_ref(ref)
    if uuid:
        config = get_provider_config_by_uuid(uuid)
        if config:
            return config
        # UUID didn't match — try as provider name
        return get_provider_config(ref, profile or "default")
    if provider:
        return get_provider_config(provider, profile or "default")
    return None
