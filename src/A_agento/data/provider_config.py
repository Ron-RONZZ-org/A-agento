"""Provider configuration storage for A-agento.

Legacy shim — delegates all storage logic to ``A.core.ai_config``.
Maintains backward-compatible dict return types.

API keys are stored separately in the system keyring (unchanged).
"""

from __future__ import annotations

from typing import Any

from A.core.ai_config import (
    ProviderConfig as _ProviderConfig,
    delete_provider_config as _core_delete,
    find_config as _core_find,
    get_fallback_order as _core_fallback_order,
    get_provider_config as _core_get,
    get_provider_config_by_uuid as _core_get_by_uuid,
    get_provider_with_fallback as _core_fallback,
    list_provider_configs as _core_list,
    parse_ref as _core_parse,
    save_provider_config as _core_save,
)

# Schema kept for backward compat with any module inspecting it
PROVIDER_CONFIG_SCHEMA = {
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

# Migration helpers — no-ops; handled by A.core.ai_config
def _ensure_uuid_column() -> None:
    pass


def _ensure_prioritato_column() -> None:
    pass


# ---------------------------------------------------------------------------
# Convert ProviderConfig dataclass → dict for backward compat
# ---------------------------------------------------------------------------


def _as_dict(cfg: _ProviderConfig | None) -> dict[str, Any] | None:
    """Convert a ProviderConfig dataclass to a plain dict.

    Args:
        cfg: A ProviderConfig instance or None.

    Returns:
        Dict with the same fields, or None.
    """
    if cfg is None:
        return None
    return {
        "uuid": cfg.uuid,
        "provider": cfg.provider,
        "profile": cfg.profile,
        "noto": cfg.noto,
        "modelo": cfg.modelo,
        "base_url": cfg.base_url,
        "prioritato": cfg.prioritato,
        "kreita_je": cfg.kreita_je,
        "modifita_je": cfg.modifita_je,
    }


# ---------------------------------------------------------------------------
# Re-exported functions (dict return types for backward compat)
# ---------------------------------------------------------------------------


def save_provider_config(
    provider: str,
    profile: str = "default",
    noto: str = "",
    modelo: str = "",
    base_url: str = "",
    prioritato: int | None = None,
) -> dict[str, Any]:
    """Save or update provider configuration.

    Delegates to ``A.core.ai_config.save_provider_config``.

    Returns:
        Dict of the saved config.
    """
    result = _core_save(provider, profile, noto, modelo, base_url, prioritato)
    return _as_dict(result)  # type: ignore[return-value]


def get_provider_config(
    provider: str,
    profile: str = "default",
) -> dict[str, Any] | None:
    """Get provider config by provider and profile.

    Returns:
        Dict or None.
    """
    return _as_dict(_core_get(provider, profile))


def get_provider_config_by_uuid(uuid: str) -> dict[str, Any] | None:
    """Get provider config by UUID (supports prefix).

    Returns:
        Dict or None.
    """
    return _as_dict(_core_get_by_uuid(uuid))


def list_provider_configs() -> list[dict[str, Any]]:
    """List all provider configs ordered by priority.

    Returns:
        List of dicts.
    """
    configs = _core_list()
    return [_as_dict(c) for c in configs if c is not None]


def delete_provider_config(
    provider: str | None = None,
    profile: str = "default",
    uuid: str | None = None,
) -> bool:
    """Delete a provider configuration.

    Returns:
        True if deleted.
    """
    return _core_delete(provider, profile, uuid)


def parse_ref(ref: str) -> tuple[str | None, str | None, str | None]:
    """Parse a provider reference.

    Returns:
        (uuid, provider, profile) tuple.
    """
    return _core_parse(ref)


def find_config(ref: str) -> dict[str, Any] | None:
    """Find a provider config by UUID, provider, or provider:profile.

    Returns:
        Dict or None.
    """
    return _as_dict(_core_find(ref))


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
