"""Provider configuration storage for A-agento.

Stores non-secret provider metadata (label, model, base URL).
API keys are stored separately in the system keyring.
"""

from __future__ import annotations

from typing import Any

from A_agento.data.storage import get_db

# Schema for the provider config table
PROVIDER_CONFIG_TABLE = "provizanto_agordoj"

PROVIDER_CONFIG_SCHEMA = {
    "provizanto_agordoj": """
        CREATE TABLE provizanto_agordoj (
            provider TEXT NOT NULL,
            profile TEXT NOT NULL DEFAULT 'default',
            noto TEXT DEFAULT '',
            modelo TEXT DEFAULT '',
            base_url TEXT DEFAULT '',
            kreita_je TEXT NOT NULL,
            modifita_je TEXT NOT NULL,
            PRIMARY KEY (provider, profile)
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
               WHERE provider = ? AND profile = ?""",
            (noto, modelo, base_url, now, provider, profile),
        )
    else:
        db.execute(
            """INSERT INTO provizanto_agordoj
               (provider, profile, noto, modelo, base_url, kreita_je, modifita_je)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (provider, profile, noto, modelo, base_url, now, now),
        )

    return {
        "provider": provider,
        "profile": profile,
        "noto": noto,
        "modelo": modelo,
        "base_url": base_url,
    }


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


def list_provider_configs() -> list[dict[str, Any]]:
    """List all provider configurations.

    Returns:
        List of config dicts ordered by provider, profile
    """
    db = get_db()
    return db.execute(
        "SELECT * FROM provizanto_agordoj ORDER BY provider, profile"
    )


def delete_provider_config(provider: str, profile: str = "default") -> bool:
    """Delete a provider configuration.

    Note: this does NOT remove the API key from the keyring.
    Use A.core.ai.save_api_key('', provider) to clear the key.

    Args:
        provider: Provider name
        profile: Profile/label

    Returns:
        True if deleted, False if not found
    """
    db = get_db()
    # Check existence first (DELETE + COUNT(*) would return 0 for missing entries too)
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
    "list_provider_configs",
    "delete_provider_config",
]
