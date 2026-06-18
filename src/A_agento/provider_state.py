"""Default provider fallback order management.

Legacy shim — delegates to ``A.core.ai_config``.
Maintains backward-compatible public API.
"""

from __future__ import annotations

from typing import Any

from A.core.ai_config import (
    get_fallback_order as _core_fallback_order,
    get_provider_with_fallback as _core_fallback,
)


def get_fallback_order() -> list[str]:
    """Get unique provider types ordered by fallback priority.

    Returns:
        List of provider type names ordered by prioritato ASC.
    """
    return _core_fallback_order()


def get_provider_with_fallback(**kwargs: Any) -> Any:
    """Get an LLM provider, trying configured providers in priority order.

    Delegates to ``A.core.ai_config.get_provider_with_fallback``.

    Returns:
        LLMProvider instance.

    Raises:
        ValueError: If no provider with available key is configured.
    """
    return _core_fallback(**kwargs)


__all__ = [
    "get_fallback_order",
    "get_provider_with_fallback",
]
