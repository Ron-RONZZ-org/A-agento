"""Shared helpers for A-agento command functions.

Provider resolution varies by input:
- None -> fallback order (A_agento.provider_state.get_provider_with_fallback)
- Bare provider name -> A.core.ai.get_provider(provider_type)
- UUID or provider:profile -> constructed from stored config + keyring key
"""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error


def get_provider_or_exit(
    provider_ref: Optional[str] = None,
):
    """Get LLM provider with error handling.

    Accepts three formats: None (fallback), bare provider name, or
    UUID / provider:profile reference.

    When auto-selected (None), shows the chosen provider to the user.
    """
    if not provider_ref:
        from A_agento.provider_state import get_provider_with_fallback
        try:
            provider = get_provider_with_fallback()
            info(
                tr_multi(
                    f"Uzas {provider.name}:{provider.model}",
                    f"Using {provider.name}:{provider.model}",
                    f"Utilise {provider.name}:{provider.model}",
                )
            )
            return provider
        except ValueError as e:
            error(str(e))
            raise typer.Exit(1) from e

    from A_agento.data.provider_config import parse_ref, find_config
    uuid, provider_name, profile = parse_ref(provider_ref)

    # Bare provider name -- use standard path
    if provider_name and not profile and not uuid:
        from A.core.ai import get_provider as _gp
        try:
            return _gp(provider_name)
        except ValueError as e:
            error(str(e))
            raise typer.Exit(1) from e

    # UUID or provider:profile -- resolve config and construct directly
    config = find_config(provider_ref)
    if config is None:
        error(tr_multi(
            f"Agordo ne trovita por '{provider_ref}'.",
            f"Configuration not found for '{provider_ref}'.",
            f"Configuration non trouvee pour '{provider_ref}'.",
        ))
        raise typer.Exit(1)

    resolved_provider = config.get("provider", provider_name or "")
    resolved_profile = config.get("profile", profile or "default")
    resolved_model = config.get("modelo", "") or None
    resolved_base_url = config.get("base_url", "") or None

    from A.core.ai import get_api_key
    api_key = get_api_key(provider=resolved_provider, profile=resolved_profile)
    if not api_key:
        error(tr_multi(
            f"Neniu API-sxlosilo por '{resolved_provider}:{resolved_profile}'.",
            f"No API key for '{resolved_provider}:{resolved_profile}'.",
            f"Aucune cle API pour '{resolved_provider}:{resolved_profile}'.",
        ))
        raise typer.Exit(1)

    try:
        return _construct_provider(resolved_provider, api_key, resolved_model, resolved_base_url)
    except Exception as e:
        error(str(e))
        raise typer.Exit(1) from e


def _construct_provider(provider_name: str, api_key: str, model: str | None = None, base_url: str | None = None):
    """Construct a provider instance directly with specific params.

    Provider names are compared case-insensitively to handle stored names
    like "Deepseek" or "DEEPSEEK" matching to the correct provider class.
    """
    from A.core.providers import OpenAICompatibleProvider, OllamaProvider

    normalized = provider_name.lower()
    if normalized == "ollama":
        return OllamaProvider(model=model or None, base_url=base_url or None)
    else:
        return OpenAICompatibleProvider(
            provider_type=normalized,
            api_key=api_key,
            model=model or None,
            base_url=base_url or None,
        )


def confirm_action(description: str) -> bool:
    """Show action preview and ask user to confirm (locale-aware).

    Args:
        description: Action description

    Returns:
        True if confirmed
    """
    from A import confirm_action as _core_confirm

    info(f"Proponita ago: {description}")
    return _core_confirm(tr_multi("Cu plenumi?", "Execute?", "Executer?"))


__all__ = [
    "get_provider_or_exit",
    "confirm_action",
]
