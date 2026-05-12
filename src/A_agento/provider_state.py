"""Default provider fallback order management.

A-agento owns the ordered list of fallback providers. The order is
determined by the `prioritato` column (lower = tried first) and
`kreita_je` (newer = tried first for equal prioritato).

This module provides the sync between A-agento's provider config DB
and the fallback logic used when no explicit provider is specified.
"""

from __future__ import annotations

from typing import Any

from A.core.ai import get_provider as _core_get_provider
from A.core.providers import _resolve_api_key


def get_fallback_order() -> list[str]:
    """Get unique provider types ordered by fallback priority.

    Returns list of unique provider type names, ordered by
    prioritato ASC, kreita_je DESC. Lower prioritato = tried first.
    """
    from A_agento.data.provider_config import list_provider_configs

    configs = list_provider_configs()
    seen: set[str] = set()
    ordered: list[str] = []
    for c in configs:
        pt = c.get("provider", "").lower()
        if pt and pt not in seen:
            seen.add(pt)
            ordered.append(pt)
    return ordered


def get_provider_with_fallback(**kwargs: Any) -> Any:
    """Get an LLM provider, trying configured providers in priority order.

    Tries each configured provider type in `prioritato` order.
    Skips providers without an available API key.

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If no provider with available key is configured
    """
    order = get_fallback_order()

    for pt in order:
        if pt == "ollama" or _resolve_api_key(pt):
            try:
                return _core_get_provider(pt, **kwargs)
            except Exception:
                continue

    raise ValueError(
        f"No configured provider available among: {order}. "
        f"Add API keys with 'A agento agordi aldoni'."
    )


__all__ = [
    "get_fallback_order",
    "get_provider_with_fallback",
]
