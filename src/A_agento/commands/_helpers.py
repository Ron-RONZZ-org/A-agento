"""Shared helpers for A-agento command functions."""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error


def get_provider_or_exit(
    provider_type: Optional[str] = None,
):
    """Get LLM provider with error handling.

    Args:
        provider_type: Provider type override

    Returns:
        LLMProvider instance
    """
    from A.core.ai import get_provider

    try:
        return get_provider(provider_type)
    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e


def confirm_action(description: str) -> bool:
    """Show action preview and ask user to confirm.

    Args:
        description: Action description

    Returns:
        True if confirmed
    """
    info(f"Proponita ago: {description}")
    return typer.confirm(tr_multi("Ĉu plenumi?", "Execute?", "Exécuter?"))


__all__ = [
    "get_provider_or_exit",
    "confirm_action",
]
