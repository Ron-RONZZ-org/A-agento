"""A-agento agordo — provider configuration commands.

Sub-app for the `agordo` command group.

Commands:
- default: Set default LLM provider
- sxlosilo: Configure API key for a provider
- ls: Show current provider configuration
- testi: Test provider connectivity
"""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, warning
from A.core.ai import (
    get_provider,
    save_api_key,
    get_api_key,
    get_default_provider,
    set_default_provider,
)
from A_agento.data.provider_config import (
    save_provider_config,
    get_provider_config,
    list_provider_configs,
    delete_provider_config,
)

# ── Sub-app definition ────────────────────────────────────────────────────

agordo_app = typer.Typer(
    name="agordo",
    help=tr_multi(
        "Agordi A-agento-provizanton kaj ŝlosilojn",  # eo
        "Configure A-agento provider and API keys",  # en
        "Configurer le fournisseur A-agento et les clés API",  # fr
    ),
    no_args_is_help=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────

VALID_PROVIDERS = ("huggingface", "deepseek", "openai", "ollama")


def _validate_provider(provizanto: str) -> None:
    """Validate provider name and exit if invalid.

    Args:
        provizanto: Provider name to validate
    """
    if provizanto not in VALID_PROVIDERS:
        error(
            tr_multi(
                f"Nevalida provizanto: {provizanto}. Validaj: {', '.join(VALID_PROVIDERS)}",  # eo
                f"Invalid provider: {provizanto}. Valid: {', '.join(VALID_PROVIDERS)}",  # en
                f"Fournisseur invalide: {provizanto}. Valides: {', '.join(VALID_PROVIDERS)}",  # fr
            )
        )
        raise typer.Exit(1)


def _get_provider_or_exit(
    provider_type: Optional[str] = None,
) -> any:
    """Get LLM provider with error handling.

    Args:
        provider_type: Provider type override

    Returns:
        LLMProvider instance
    """
    try:
        return get_provider(provider_type)
    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e


# ── default — set default provider ────────────────────────────────────────


@agordo_app.command("default")
def default(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto (huggingface/deepseek/openai/ollama)",  # eo
            "Provider (huggingface/deepseek/openai/ollama)",  # en
            "Fournisseur (huggingface/deepseek/openai/ollama)",  # fr
        ),
    ),
) -> None:
    """Set the default LLM provider.

    Examples:
        agento agordo default ollama
        agento agordo default openai
    """
    _validate_provider(provizanto)

    try:
        set_default_provider(provizanto)
        success(
            tr_multi(
                f"Implicitita provizanto: {provizanto}",  # eo
                f"Default provider: {provizanto}",  # en
                f"Fournisseur par défaut: {provizanto}",  # fr
            )
        )
    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e


# ── sxlosilo — configure API key ──────────────────────────────────────────


@agordo_app.command("sxlosilo")
def sxlosilo(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto (huggingface/deepseek/openai)",  # eo
            "Provider (huggingface/deepseek/openai)",  # en
            "Fournisseur (huggingface/deepseek/openai)",  # fr
        ),
    ),
    key: Optional[str] = typer.Option(
        None,
        "--key",
        "-k",
        help=tr_multi(
            "API-ŝlosilo (se ne donita, petita interage)",  # eo
            "API key (if omitted, prompted interactively)",  # en
            "Clé API (si omise, demandée interactivement)",  # fr
        ),
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        "-b",
        help=tr_multi(
            "API-baza URL (por OpenAI-kongruaj finpunktoj)",  # eo
            "API base URL (for OpenAI-compatible endpoints)",  # fr
            "URL de base API (pour les points de terminaison compatibles OpenAI)",  # fr
        ),
    ),
    noto: Optional[str] = typer.Option(
        None,
        "--noto",
        "-n",
        help=tr_multi(
            "Etikedo por la ŝlosilo (ekz. 'laboro', 'persona')",  # eo
            "Label for this key (e.g. 'work', 'personal')",  # en
            "Étiquette pour cette clé (ex. 'travail', 'personnel')",  # fr
        ),
    ),
    modelo: Optional[str] = typer.Option(
        None,
        "--modelo",
        "-m",
        help=tr_multi(
            "Modelo-nomo (ekz. 'gpt-4', 'deepseek-chat')",  # eo
            "Model name (e.g. 'gpt-4', 'deepseek-chat')",  # en
            "Nom du modèle (ex. 'gpt-4', 'deepseek-chat')",  # fr
        ),
    ),
) -> None:
    """Configure an API key for a provider.

    Stores the API key in the system keyring (never in plaintext files).
    Provider metadata (label, model, base URL) is stored in A-agento's database.

    If --key is omitted, you will be prompted interactively (input hidden).

    Examples:
        agento agordo sxlosilo openai
        agento agordo sxlosilo huggingface --key hf_abc123
        agento agordo sxlosilo openai --key sk-... --base-url https://custom.endpoint/v1
        agento agordo sxlosilo openai --noto work --modelo gpt-4
    """
    if provizanto == "ollama":
        warning(
            tr_multi(
                "Ollama ne bezonas API-ŝlosilon. Uzu 'agordo default ollama'.",  # eo
                "Ollama does not need an API key. Use 'agordo default ollama'.",  # en
                "Ollama n'a pas besoin de clé API. Utilisez 'agordo default ollama'.",  # fr
            )
        )
        return

    _validate_provider(provizanto)

    # Interactive prompt if no key provided
    if not key:
        import getpass

        info(
            tr_multi(
                f"Enigu API-ŝlosilon por {provizanto}:",  # eo
                f"Enter API key for {provizanto}:",  # en
                f"Entrez la clé API pour {provizanto}:",  # fr
            )
        )
        key = getpass.getpass("")
        if not key:
            error(
                tr_multi(
                    "Neniu ŝlosilo enigita. Nuligita.",  # eo
                    "No key entered. Cancelled.",  # en
                    "Aucune clé saisie. Annulé.",  # fr
                )
            )
            raise typer.Exit(1)

    # Save to keyring
    profile = noto or "default"
    saved = save_api_key(key, provider=provizanto, profile=profile)
    if not saved:
        error(
            tr_multi(
                "Ne povis konservi ŝlosilon en ŝlosilaron.",  # eo
                "Failed to save key to system keyring.",  # en
                "Impossible d'enregistrer la clé dans le trousseau.",  # fr
            )
        )
        raise typer.Exit(1)

    # Save metadata to SQLite
    save_provider_config(
        provider=provizanto,
        profile=profile,
        noto=noto or "",
        modelo=modelo or "",
        base_url=base_url or "",
    )

    # If this is the first key, set as default provider
    existing = list_provider_configs()
    if len(existing) <= 1:
        set_default_provider(provizanto)

    success(
        tr_multi(
            f"Ŝlosilo por {provizanto} konservita en ŝlosilaro.",  # eo
            f"API key for {provizanto} saved to system keyring.",  # en
            f"Clé API pour {provizanto} enregistrée dans le trousseau.",  # fr
        )
    )


# ── montri — show configuration ───────────────────────────────────────────


@agordo_app.command("ls")
def agordo_ls() -> None:
    """Show current provider configuration.

    Displays the default provider, all configured API keys (masked),
    and any associated metadata (model, base URL, labels).

    API keys are NEVER displayed in full — only the last 4 characters.

    Examples:
        agento agordo ls
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Default provider
    default = get_default_provider()
    info(
        tr_multi(
            f"Implicitita provizanto: {default}",  # eo
            f"Default provider: {default}",  # en
            f"Fournisseur par défaut: {default}",  # fr
        )
    )

    # Configured providers
    configs = list_provider_configs()

    if not configs:
        info(
            tr_multi(
                "Neniuj provizantoj agorditaj. Uzu 'agordo sxlosilo' por aldoni ŝlosilon.",  # eo
                "No providers configured. Use 'agordo sxlosilo' to add a key.",  # en
                "Aucun fournisseur configuré. Utilisez 'agordo sxlosilo' pour ajouter une clé.",  # fr
            )
        )
        return

    table = Table(title=tr_multi('Provizantoj', 'Providers', 'Fournisseurs'))
    table.add_column(tr_multi('Provizanto', 'Provider', 'Fournisseur'), style="cyan")
    table.add_column(tr_multi("Sxlosilo", "Key", "Cle"), style="yellow")
    table.add_column(tr_multi('Modelo', 'Model', 'Modele'), style="green")
    table.add_column(tr_multi('Baza URL', 'Base URL', 'URL de base'), style="blue")
    table.add_column(tr_multi('Etikedo', 'Label', 'Etiquette'), style="magenta")

    for cfg in configs:
        prov = cfg["provider"]
        prof = cfg.get("profile", "default")
        api_key = get_api_key(provider=prov, profile=prof)

        if api_key:
            masked = "..." + api_key[-4:]
        else:
            masked = tr_multi(
                "mankas",  # eo
                "missing",  # en
                "manquant",  # fr
            )

        table.add_row(
            prov,
            masked,
            cfg.get("modelo", "") or "-",
            cfg.get("base_url", "") or "-",
            cfg.get("noto", "") or "-",
        )

    console.print(table)


@agordo_app.command("montri", hidden=True)
def montri() -> None:
    """[DEPRECATED] Use 'agordo ls' instead."""
    agordo_ls()


# ── testi — test provider connectivity ────────────────────────────────────


@agordo_app.command("testi")
def testi(
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "Provizanto por testi (implicitite: tiu implicita)",  # eo
            "Provider to test (default: the default provider)",  # en
            "Fournisseur à tester (défaut: le fournisseur par défaut)",  # fr
        ),
    ),
) -> None:
    """Test provider connectivity with a minimal prompt.

    Sends a simple test prompt ("Reply with exactly one word: OK")
    and checks for a valid response.

    Examples:
        agento agordo testi
        agento agordo testi --provizanto openai
    """
    provider = _get_provider_or_exit(provizanto)

    info(
        tr_multi(
            f"Testas {provider.name}...",  # eo
            f"Testing {provider.name}...",  # en
            f"Test de {provider.name}...",  # fr
        )
    )

    try:
        result = provider.generate("Reply with exactly one word: OK")
        clean = result.strip().lower().rstrip(".,!?;:")

        if "ok" in clean:
            success(
                tr_multi(
                    f"{provider.name} respondis sukcese.",  # eo
                    f"{provider.name} responded successfully.",  # en
                    f"{provider.name} a répondu avec succès.",  # fr
                )
            )
        else:
            warning(
                tr_multi(
                    f"{provider.name} respondis sed neatendite: {result[:80]}",  # eo
                    f"{provider.name} responded but unexpected: {result[:80]}",  # en
                    f"{provider.name} a répondu mais de façon inattendue: {result[:80]}",  # fr
                )
            )
    except Exception as e:
        error(
            tr_multi(
                f"{provider.name} eraro: {e}",  # eo
                f"{provider.name} error: {e}",  # en
                f"{provider.name} erreur: {e}",  # fr
            )
        )
        raise typer.Exit(1) from e


__all__ = [
    "agordo_app",
]
