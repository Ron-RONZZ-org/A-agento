from __future__ import annotations
from A import confirm_action
"""A-agento agordo CRUD commands — provider configuration management.

Commands: vidi, modifi, forigi (aldoni lives in agordo.py)
"""


from typing import List, Optional

import typer

from A import tr_multi, info, error, success, warning
from A.core.ai import get_api_key, set_default_provider, get_default_provider
from A_agento.data.provider_config import (
    save_provider_config,
    get_provider_config,
    get_provider_config_by_uuid,
    list_provider_configs,
    delete_provider_config as _delete_provider_config,
    parse_ref as _parse_ref,
    find_config as _find_config,
)


# ── vidi — view single provider ──────────────────────────────────────────


def vidi(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "UUID, provizanto-nomo, aux provizanto:profilon por vidi",
            "UUID, provider name, or provider:profile to view",
            "UUID, nom du fournisseur ou fournisseur:profil a voir",
        ),
    ),
) -> None:
    """Show detailed configuration for a single provider or profile.

    Examples:
        agento agordi vidi openai
        agento agordi vidi openai:work
        agento agordi vidi a1b2c3d4-...
    """
    from rich.console import Console
    from rich.table import Table

    config = _find_config(provizanto)
    if config is None:
        error(tr_multi(
            f"Provizanto '{provizanto}' ne trovita.",
            f"Provider '{provizanto}' not found.",
            f"Fournisseur '{provizanto}' introuvable.",
        ))
        raise typer.Exit(1)

    provider = config["provider"]
    profile = config.get("profile", "default")
    api_key = get_api_key(provider=provider, profile=profile)
    masked = ("..." + api_key[-4:]) if api_key else tr_multi("mankas", "missing", "manquant")

    console = Console()
    table = Table(title=tr_multi(
        f"Provizanto: {provider}", f"Provider: {provider}", f"Fournisseur : {provider}",
    ))
    table.add_column(tr_multi("Kampo", "Field", "Champ"), style="cyan")
    table.add_column(tr_multi("Valoro", "Value", "Valeur"), style="white")

    table.add_row(tr_multi("UUID", "UUID", "UUID"), config.get("uuid", "")[:8] or "-")
    table.add_row(tr_multi("Profilon", "Profile", "Profil"), profile)
    table.add_row(tr_multi("Sxlosilo", "Key", "Cle"), masked)
    table.add_row(tr_multi("Modelo", "Model", "Modele"), config.get("modelo", "") or "-")
    table.add_row(tr_multi("Baza URL", "Base URL", "URL de base"), config.get("base_url", "") or "-")
    table.add_row(tr_multi("Etikedo", "Label", "Etiquette"), config.get("noto", "") or "-")
    table.add_row(tr_multi("Kreita je", "Created at", "Cree le"), config.get("kreita_je", "") or "-")
    table.add_row(tr_multi("Modifita je", "Modified at", "Modifie le"), config.get("modifita_je", "") or "-")

    console.print(table)


# ── modifi — update provider ──────────────────────────────────────────────


def modifi(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "UUID, provizanto-nomo, aux provizanto:profilon por modifi",
            "UUID, provider name, or provider:profile to modify",
            "UUID, nom du fournisseur ou fournisseur:profil a modifier",
        ),
    ),
    key: Optional[str] = typer.Option(None, "--key", "-k",
        help=tr_multi("Nova API-sxlosilo", "New API key", "Nouvelle cle API")),
    base_url: Optional[str] = typer.Option(None, "--base-url", "-b",
        help=tr_multi("Nova API-baza URL", "New API base URL", "Nouvelle URL de base API")),
    noto: Optional[str] = typer.Option(None, "--noto", "-n",
        help=tr_multi("Nova etikedo", "New label", "Nouvelle etiquette")),
    modelo: Optional[str] = typer.Option(None, "--modelo", "-m",
        help=tr_multi("Nova modelo-nomo", "New model name", "Nouveau nom du modele")),
) -> None:
    """Modify an existing provider configuration.

    All options are optional — only specified fields are updated.
    If no options are provided, runs interactively with current values.

    Examples:
        agento agordi modifi openai --key sk-new
        agento agordi modifi openai:work --modelo gpt-4
    """
    config = _find_config(provizanto)
    if config is None:
        error(tr_multi(
            f"Provizanto '{provizanto}' ne trovita.",
            f"Provider '{provizanto}' not found.",
            f"Fournisseur '{provizanto}' introuvable.",
        ))
        raise typer.Exit(1)

    provider = config["provider"]
    profile = config.get("profile", "default")

    if key:
        from A.core.ai import save_api_key as _save_key
        _save_key(key, provider=provider, profile=profile)

    # Interactive mode: if no flags given, prompt with current values
    if not any([key, base_url, noto, modelo]):
        info(tr_multi(
            f"Modifi agordojn por {provider}:{profile} (premu Enter por konservi):",
            f"Modify settings for {provider}:{profile} (Enter to keep):",
            f"Modifier les parametres pour {provider}:{profile} (Entree pour garder):",
        ))
        new_base_url = typer.prompt(
            tr_multi("Baza URL", "Base URL", "URL de base"),
            default=config.get("base_url", "") or "",
        )
        if new_base_url != config.get("base_url", ""):
            base_url = new_base_url
        new_noto = typer.prompt(
            tr_multi("Etikedo", "Label", "Etiquette"),
            default=config.get("noto", "") or "",
        )
        if new_noto != config.get("noto", ""):
            noto = new_noto
        new_modelo = typer.prompt(
            tr_multi("Modelo", "Model", "Modele"),
            default=config.get("modelo", "") or "",
        )
        if new_modelo != config.get("modelo", ""):
            modelo = new_modelo
        if not any([base_url, noto, modelo]):
            info(tr_multi("Neniuj sangxoj. Nuligita.", "No changes. Cancelled.", "Aucun changement. Annule."))
            return

    save_provider_config(
        provider=provider,
        profile=profile,
        noto=noto if noto is not None else config.get("noto", ""),
        modelo=modelo if modelo is not None else config.get("modelo", ""),
        base_url=base_url if base_url is not None else config.get("base_url", ""),
    )
    success(tr_multi(
        f"Agordoj por {provider}:{profile} gxisdatigitaj.",
        f"Settings for {provider}:{profile} updated.",
        f"Parametres pour {provider}:{profile} mis a jour.",
    ))


# ── forigi — delete provider(s) ──────────────────────────────────────────


def _maybe_reassign_default(deleted_provider: str) -> None:
    """If the deleted provider was the default, reassign to a safe fallback."""
    current_default = get_default_provider()
    if deleted_provider != current_default:
        return
    remaining = list_provider_configs()
    if not remaining:
        set_default_provider("ollama")
        info(tr_multi(
            "Implicitita provizanto rekomencigita al ollama.",
            "Default provider reset to ollama.",
            "Fournisseur par defaut reinitialise a ollama.",
        ))
    else:
        warning(tr_multi(
            "La implicita provizanto estis forigita. Uzu 'agordi default' por agordi novan.",
            "The default provider was deleted. Use 'agordi default' to set a new one.",
            "Le fournisseur par defaut a ete supprime. Utilisez 'agordi default' pour en definir un nouveau.",
        ))


def _delete_one(ref: str, keyring: bool) -> bool:
    """Delete a single provider config by UUID, provider, or provider:profile.

    Args:
        ref: UUID, provider name, or "provider:profile".
        keyring: Whether to also clear the API key from keyring.

    Returns:
        True if deleted, False if not found.
    """
    uuid, provider, profile = _parse_ref(ref)
    config = _find_config(ref)
    if config is None:
        return False

    provider_name = config["provider"]
    profile_name = config.get("profile", "default")
    config_uuid = config.get("uuid")
    deleted = _delete_provider_config(
        uuid=config_uuid,
        provider=provider_name,
        profile=profile_name,
    )
    if not deleted:
        return False

    if keyring:
        from A.core.ai import save_api_key
        save_api_key("", provider=provider_name, profile=profile_name)

    _maybe_reassign_default(provider_name)
    return True


def forigi(
    provizantoj: List[str] = typer.Argument(
        ...,
        help=tr_multi(
            "UUID, provizanto-nomo(j), aux provizanto:profilon por forigi (unu aux pluraj)",
            "UUID, provider name(s), or provider:profile to delete (one or more)",
            "UUID, nom(s) du fournisseur ou fournisseur:profil a supprimer (un ou plusieurs)",
        ),
    ),
    keyring: bool = typer.Option(False, "--keyring",
        help=tr_multi("Ankau forigi API-sxlosilon el sxlosilaro", "Also delete API key from keyring", "Supprimer aussi la cle API du trousseau")),
    jes: bool = typer.Option(False, "--jes", "-y",
        help=tr_multi("Rekte konfirmi sen prompto", "Confirm directly without prompt", "Confirmer directement sans invite")),
) -> None:
    """Delete one or more provider configurations.

    Accepts multiple positional arguments: UUIDs, provider names,
    or "provider:profile" syntax.

    Examples:
        agento agordi forigi openai
        agento agordi forigi openai:work deepseek
        agento agordi forigi a1b2c3d4-... openai:personal -y
    """
    if not jes and len(provizantoj) > 1:
        confirm = confirm_action(
            tr_multi(
                f"Forigi {len(provizantoj)} agordojn?",
                f"Delete {len(provizantoj)} configurations?",
                f"Supprimer {len(provizantoj)} configurations?",
            ),
            default=False,
        )
        if not confirm:
            info(tr_multi("Nuligita.", "Cancelled.", "Annule."))
            return

    deleted = 0
    not_found = []
    for ref in provizantoj:
        if _delete_one(ref, keyring):
            deleted += 1
        else:
            not_found.append(ref)

    if deleted:
        success(tr_multi(
            f"Forigis {deleted} agordojn.",
            f"Deleted {deleted} configurations.",
            f"Supprime {deleted} configurations.",
        ))
    for ref in not_found:
        warning(tr_multi(
            f"Ne trovita: {ref}",
            f"Not found: {ref}",
            f"Introuvable: {ref}",
        ))


__all__ = [
    "vidi",
    "modifi",
    "forigi",
]
