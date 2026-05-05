"""A-agento agordo CRUD commands — provider configuration management.

Commands: vidi, modifi, forigi (aldoni lives in agordo.py)
"""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, warning
from A.core.ai import get_api_key, set_default_provider, get_default_provider
from A_agento.data.provider_config import (
    save_provider_config,
    get_provider_config,
    list_provider_configs,
    delete_provider_config as _delete_provider_config,
)


# ── vidi — view single provider ──────────────────────────────────────────────


def vidi(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto-nomo por vidi",  # eo
            "Provider name to view",  # en
            "Nom du fournisseur à voir",  # fr
        ),
    ),
) -> None:
    """Show detailed configuration for a single provider.

    Displays the API key status (masked), model, base URL,
    label, and timestamps.

    API keys are NEVER displayed in full — only the last 4 characters.

    Examples:
        agento agordo vidi openai
        agento agordo vidi my-custom-endpoint
    """
    from rich.console import Console
    from rich.table import Table

    config = get_provider_config(provizanto)
    if config is None:
        error(
            tr_multi(
                f"Provizanto '{provizanto}' ne trovita. Uzu 'agordo aldoni' por aldoni.",  # eo
                f"Provider '{provizanto}' not found. Use 'agordo aldoni' to add.",  # en
                f"Fournisseur '{provizanto}' introuvable. Utilisez 'agordo aldoni' pour ajouter.",  # fr
            )
        )
        raise typer.Exit(1)

    profile = config.get("profile", "default")
    api_key = get_api_key(provider=provizanto, profile=profile)
    masked = ("..." + api_key[-4:]) if api_key else tr_multi("mankas", "missing", "manquant")

    console = Console()
    table = Table(title=tr_multi(f"Provizanto: {provizanto}", f"Provider: {provizanto}", f"Fournisseur : {provizanto}"))
    table.add_column(tr_multi("Kampo", "Field", "Champ"), style="cyan")
    table.add_column(tr_multi("Valoro", "Value", "Valeur"), style="white")

    table.add_row(tr_multi("Profilon", "Profile", "Profil"), profile)
    table.add_row(tr_multi("Ŝlosilo", "Key", "Clé"), masked)
    table.add_row(tr_multi("Modelo", "Model", "Modèle"), config.get("modelo", "") or "-")
    table.add_row(tr_multi("Baza URL", "Base URL", "URL de base"), config.get("base_url", "") or "-")
    table.add_row(tr_multi("Etikedo", "Label", "Étiquette"), config.get("noto", "") or "-")
    table.add_row(tr_multi("Kreita je", "Created at", "Créé le"), config.get("kreita_je", "") or "-")
    table.add_row(tr_multi("Modifita je", "Modified at", "Modifié le"), config.get("modifita_je", "") or "-")

    console.print(table)


# ── modifi — update provider ──────────────────────────────────────────────────


def modifi(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto-nomo por modifi",  # eo
            "Provider name to modify",  # en
            "Nom du fournisseur à modifier",  # fr
        ),
    ),
    key: Optional[str] = typer.Option(
        None,
        "--key",
        "-k",
        help=tr_multi(
            "Nova API-ŝlosilo",  # eo
            "New API key",  # en
            "Nouvelle clé API",  # fr
        ),
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        "-b",
        help=tr_multi(
            "Nova API-baza URL",  # eo
            "New API base URL",  # en
            "Nouvelle URL de base API",  # fr
        ),
    ),
    noto: Optional[str] = typer.Option(
        None,
        "--noto",
        "-n",
        help=tr_multi(
            "Nova etikedo",  # eo
            "New label",  # en
            "Nouvelle étiquette",  # fr
        ),
    ),
    modelo: Optional[str] = typer.Option(
        None,
        "--modelo",
        "-m",
        help=tr_multi(
            "Nova modelo-nomo",  # eo
            "New model name",  # en
            "Nouveau nom du modèle",  # fr
        ),
    ),
) -> None:
    """Modify an existing provider configuration.

    All options are optional — only specified fields are updated.
    If no options are provided, runs interactively with current values
    as defaults.

    Examples:
        agento agordo modifi openai --key sk-new
        agento agordo modifi openai --base-url https://new.endpoint/v1
        agento agordo modifi openai  # interactive mode
    """
    config = get_provider_config(provizanto)
    if config is None:
        error(
            tr_multi(
                f"Provizanto '{provizanto}' ne trovita. Uzu 'agordo aldoni' por aldoni unue.",  # eo
                f"Provider '{provizanto}' not found. Use 'agordo aldoni' first.",  # en
                f"Fournisseur '{provizanto}' introuvable. Utilisez 'agordo aldoni' d'abord.",  # fr
            )
        )
        raise typer.Exit(1)

    profile = config.get("profile", "default")

    if key:
        from A.core.ai import save_api_key as _save_key
        _save_key(key, provider=provizanto, profile=profile)

    # Interactive mode: if no flags given, prompt with current values
    if not any([key, base_url, noto, modelo]):
        info(
            tr_multi(
                f"Modifi agordojn por {provizanto} (premu Enter por konservi nunan valoron):",  # eo
                f"Modify settings for {provizanto} (press Enter to keep current value):",  # en
                f"Modifier les paramètres pour {provizanto} (appuyez sur Enter pour conserver la valeur actuelle):",  # fr
            )
        )

        new_base_url = typer.prompt(
            tr_multi("Baza URL", "Base URL", "URL de base"),
            default=config.get("base_url", "") or "",
        )
        if new_base_url != config.get("base_url", ""):
            base_url = new_base_url

        new_noto = typer.prompt(
            tr_multi("Etikedo", "Label", "Étiquette"),
            default=config.get("noto", "") or "",
        )
        if new_noto != config.get("noto", ""):
            noto = new_noto

        new_modelo = typer.prompt(
            tr_multi("Modelo", "Model", "Modèle"),
            default=config.get("modelo", "") or "",
        )
        if new_modelo != config.get("modelo", ""):
            modelo = new_modelo

        if not any([base_url, noto, modelo]):
            info(
                tr_multi(
                    "Neniuj ŝanĝoj. Nuligita.",  # eo
                    "No changes. Cancelled.",  # en
                    "Aucun changement. Annulé.",  # fr
                )
            )
            return

    # Save metadata updates
    save_provider_config(
        provider=provizanto,
        profile=profile,
        noto=noto if noto is not None else config.get("noto", ""),
        modelo=modelo if modelo is not None else config.get("modelo", ""),
        base_url=base_url if base_url is not None else config.get("base_url", ""),
    )

    success(
        tr_multi(
            f"Agordoj por {provizanto} ĝisdatigitaj.",  # eo
            f"Settings for {provizanto} updated.",  # en
            f"Paramètres pour {provizanto} mis à jour.",  # fr
        )
    )


# ── forigi — delete provider ─────────────────────────────────────────────────


def _maybe_reassign_default(deleted_provider: str) -> None:
    """If the deleted provider was the default, reassign to a safe fallback.

    Args:
        deleted_provider: The provider that was just deleted
    """
    current_default = get_default_provider()
    if deleted_provider != current_default:
        return

    remaining = list_provider_configs()
    if not remaining:
        set_default_provider("ollama")
        info(
            tr_multi(
                "Implicitita provizanto rekomencigita al ollama.",  # eo
                "Default provider reset to ollama.",  # en
                "Fournisseur par défaut réinitialisé à ollama.",  # fr
            )
        )
    else:
        warning(
            tr_multi(
                "La implicita provizanto estis forigita. Uzu 'agordo default' por agordi novan.",  # eo
                "The default provider was deleted. Use 'agordo default' to set a new one.",  # en
                "Le fournisseur par défaut a été supprimé. Utilisez 'agordo default' pour en définir un nouveau.",  # fr
            )
        )


def forigi(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto-nomo por forigi",  # eo
            "Provider name to delete",  # en
            "Nom du fournisseur à supprimer",  # fr
        ),
    ),
    keyring: bool = typer.Option(
        False,
        "--keyring",
        help=tr_multi(
            "Ankaŭ forigi API-ŝlosilon el ŝlosilaro",  # eo
            "Also delete the API key from system keyring",  # en
            "Supprimer également la clé API du trousseau",  # fr
        ),
    ),
    jes: bool = typer.Option(
        False,
        "--jes",
        "-y",
        help=tr_multi(
            "Rekte konfirmi sen prompto",  # eo
            "Confirm directly without prompt",  # en
            "Confirmer directement sans invite",  # fr
        ),
    ),
) -> None:
    """Delete a provider configuration.

    Removes the provider metadata from A-agento's database.
    API keys are NOT removed from the system keyring unless --keyring is used.

    If this was the default provider, a fallback is set automatically.

    Examples:
        agento agordo forigi openai
        agento agordo forigi openai --keyring -y
    """
    config = get_provider_config(provizanto)
    if config is None:
        error(
            tr_multi(
                f"Provizanto '{provizanto}' ne trovita.",  # eo
                f"Provider '{provizanto}' not found.",  # en
                f"Fournisseur '{provizanto}' introuvable.",  # fr
            )
        )
        raise typer.Exit(1)

    if not jes:
        confirm = typer.confirm(
            tr_multi(
                f"Forigi agordojn por {provizanto}?",  # eo
                f"Delete configuration for {provizanto}?",  # en
                f"Supprimer la configuration pour {provizanto}?",  # fr
            ),
            default=False,
        )
        if not confirm:
            info(
                tr_multi(
                    "Nuligita.",  # eo
                    "Cancelled.",  # en
                    "Annulé.",  # fr
                )
            )
            return

    deleted = _delete_provider_config(provizanto)
    if not deleted:
        error(
            tr_multi(
                f"Ne povis forigi agordojn por {provizanto}.",  # eo
                f"Failed to delete configuration for {provizanto}.",  # en
                f"Impossible de supprimer la configuration pour {provizanto}.",  # fr
            )
        )
        raise typer.Exit(1)

    if keyring:
        profile = config.get("profile", "default")
        from A.core.ai import save_api_key as _save_key
        _save_key("", provider=provizanto, profile=profile)

    _maybe_reassign_default(provizanto)

    success(
        tr_multi(
            f"Agordoj por {provizanto} forigitaj.",  # eo
            f"Configuration for {provizanto} deleted.",  # en
            f"Configuration pour {provizanto} supprimée.",  # fr
        )
    )


__all__ = [
    "vidi",
    "modifi",
    "forigi",
]
