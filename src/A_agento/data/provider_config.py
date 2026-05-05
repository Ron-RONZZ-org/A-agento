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
    """Get provider configuration by UUID.

    Args:
        uuid: Entry UUID

    Returns:
        Config dict or None
    """
    db = get_db()
    return db.execute_one(
        "SELECT * FROM provizanto_agordoj WHERE uuid = ?",
        (uuid,),
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
]
