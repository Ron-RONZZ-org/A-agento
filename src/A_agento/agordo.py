"""A-agento agordo — provider configuration commands.

Sub-app for the `agordi` command group.

Commands (run via `agento agordi <command>`):
- default: Set default LLM provider (sets prioritato=0)
- aldoni: Add API key for a provider
- vidi: View single provider configuration
- modifi: Update existing provider configuration
- forigi: Delete provider configuration
- ls: Show all configured providers (in fallback order)
- testi: Test provider connectivity
"""

from __future__ import annotations

from typing import Optional

import getpass
import typer

from A import tr_multi, info, error, success, warning
from A.core.ai import get_provider, save_api_key, get_api_key
from A_agento.data.provider_config import (
    save_provider_config,
    list_provider_configs,
    find_config,
)
from A_agento.agordo_crud import vidi, modifi, forigi

# ── Sub-app definition ────────────────────────────────────────────────────

agordo_app = typer.Typer(
    name="agordi",
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
    """Validate provider name and exit if invalid."""
    if provizanto not in VALID_PROVIDERS:
        error(
            tr_multi(
                f"Nevalida provizanto: {provizanto}. Validaj: {', '.join(VALID_PROVIDERS)}",  # eo
                f"Invalid provider: {provizanto}. Valid: {', '.join(VALID_PROVIDERS)}",  # en
                f"Fournisseur invalide: {provizanto}. Valides: {', '.join(VALID_PROVIDERS)}",  # fr
            )
        )
        raise typer.Exit(1)


def _get_provider_for_test(provider_type: Optional[str] = None):
    """Get LLM provider with error handling (for testi command)."""
    try:
        if provider_type:
            return get_provider(provider_type)
        from A_agento.provider_state import get_provider_with_fallback
        return get_provider_with_fallback()
    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e


# ── aldoni — add API key ────────────────────────────────────────────────────


@agordo_app.command("aldoni", help=tr_multi(
    "Aldoni API-ŝlosilon por provizanto",  # eo
    "Add API key for a provider",  # en
    "Ajouter une clé API pour un fournisseur",  # fr
))
def aldoni(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto-nomo (huggingface, deepseek, openai, aux) iu ajn nomo por OpenAI-kongrua finpunkto)",  # eo
            "Provider name (huggingface, deepseek, openai, or any name for OpenAI-compatible endpoint)",  # en
            "Nom du fournisseur (huggingface, deepseek, openai, ou tout nom pour un point de terminaison compatible OpenAI)",  # fr
        ),
    ),
    key: Optional[str] = typer.Option(
        None, "--key", "-k",
        help=tr_multi("API-ŝlosilo (se ne donita, petita interage)", "API key (if omitted, prompted interactively)", "Clé API (si omise, demandée interactivement)"),
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", "-b",
        help=tr_multi("API-baza URL (por OpenAI-kongruaj finpunktoj)", "API base URL (for OpenAI-compatible endpoints)", "URL de base API (pour les points de terminaison compatibles OpenAI)"),
    ),
    noto: Optional[str] = typer.Option(
        None, "--noto", "-n",
        help=tr_multi("Etikedo por la ŝlosilo (ekz. 'laboro', 'persona')", "Label for this key (e.g. 'work', 'personal')", "Étiquette pour cette clé (ex. 'travail', 'personnel')"),
    ),
    modelo: Optional[str] = typer.Option(
        None, "--modelo", "-m",
        help=tr_multi("Modelo-nomo (ekz. 'gpt-4', 'deepseek-chat')", "Model name (e.g. 'gpt-4', 'deepseek-chat')", "Nom du modèle (ex. 'gpt-4', 'deepseek-chat')"),
    ),
    prioritato: Optional[int] = typer.Option(
        None, "--prioritato", "-p",
        help=tr_multi("Prioritato (pli malalta = unue provita; implicite: 0 = plej alta)", "Priority (lower = tried first; default: 0 = highest)", "Priorité (plus bas = essayé en premier; défaut: 0 = plus haut)"),
    ),
) -> None:
    """Add an API key for a provider. Stores key in system keyring, metadata in SQLite."""
    if provizanto == "ollama":
        warning(tr_multi("Ollama ne bezonas API-ŝlosilon. Uzu 'agordi default ollama'.", "Ollama does not need an API key. Use 'agordi default ollama'.", "Ollama n'a pas besoin de clé API. Utilisez 'agordi default ollama'."))
        return

    # Interactive mode: if no key provided, prompt for all options
    if not key:
        info(tr_multi(f"Enigu API-ŝlosilon por {provizanto}:", f"Enter API key for {provizanto}:", f"Entrez la clé API pour {provizanto}:"))
        key = getpass.getpass("")
        if not key:
            error(tr_multi("Neniu ŝlosilo enigita. Nuligita.", "No key entered. Cancelled.", "Aucune clé saisie. Annulé."))
            raise typer.Exit(1)

        if not base_url:
            base_url = typer.prompt(tr_multi("API-baza URL (opcia):", "API base URL (optional):", "URL de base API (optionnelle):"), default="")
        if not noto:
            noto = typer.prompt(tr_multi("Etikedo por la ŝlosilo (opcia):", "Label for this key (optional):", "Étiquette pour cette clé (optionnelle):"), default="")
        if not modelo:
            modelo = typer.prompt(tr_multi("Modelo-nomo (opcia):", "Model name (optional):", "Nom du modèle (optionnel):"), default="")

    # Save to keyring
    profile = noto or "default"
    saved = save_api_key(key, provider=provizanto, profile=profile)
    if not saved:
        error(tr_multi("Ne povis konservi ŝlosilon en ŝlosilaron.", "Failed to save key to system keyring.", "Impossible d'enregistrer la clé dans le trousseau."))
        raise typer.Exit(1)

    # Save metadata to SQLite (prioritato auto-assigned by save_provider_config)
    save_provider_config(provider=provizanto, profile=profile, noto=noto or "", modelo=modelo or "", base_url=base_url or "", prioritato=prioritato)

    success(tr_multi(f"Ŝlosilo por {provizanto} konservita en ŝlosilaro.", f"API key for {provizanto} saved to system keyring.", f"Clé API pour {provizanto} enregistrée dans le trousseau."))


# ── Register CRUD commands from agordo_crud ────────────────────────────────

agordo_app.command(
    name="vidi",
    help=tr_multi("Vidi unuopan provizantan agordon", "View single provider configuration", "Voir la configuration d'un fournisseur"),
)(vidi)

agordo_app.command(
    name="modifi",
    help=tr_multi("Modifi ekzistantan provizantan agordon", "Modify existing provider configuration", "Modifier la configuration d'un fournisseur existant"),
)(modifi)

agordo_app.command(
    name="forigi",
    help=tr_multi("Forigi provizantan agordon", "Delete provider configuration", "Supprimer la configuration d'un fournisseur"),
)(forigi)

# ── Deprecated aliases for aldoni ──────────────────────────────────────────


@agordo_app.command("slosilo", hidden=True, help=tr_multi(
    "[Eksdata] Uzu 'agordi aldoni' anstatauxe", "[DEPRECATED] Use 'agordi aldoni' instead", "[Obsolète] Utilisez 'agordi aldoni' à la place",
))
def slosilo_deprecated(
    provizanto: str = typer.Argument(...),
    key: Optional[str] = typer.Option(None, "--key", "-k"),
    base_url: Optional[str] = typer.Option(None, "--base-url", "-b"),
    noto: Optional[str] = typer.Option(None, "--noto", "-n"),
    modelo: Optional[str] = typer.Option(None, "--modelo", "-m"),
) -> None:
    """[DEPRECATED] Use 'agordi aldoni' instead."""
    warning(tr_multi("'agordi slosilo' estas eksdata. Uzu 'agordi aldoni'.", "'agordi slosilo' is deprecated. Use 'agordi aldoni'.", "'agordi slosilo' est obsolète. Utilisez 'agordi aldoni'."))
    aldoni(provizanto, key=key, base_url=base_url, noto=noto, modelo=modelo)


@agordo_app.command("sxlosilo", hidden=True, help=tr_multi(
    "[Eksdata] Uzu 'agordi aldoni' anstatauxe", "[DEPRECATED] Use 'agordi aldoni' instead", "[Obsolète] Utilisez 'agordi aldoni' à la place",
))
def sxlosilo_deprecated(
    provizanto: str = typer.Argument(...),
    key: Optional[str] = typer.Option(None, "--key", "-k"),
    base_url: Optional[str] = typer.Option(None, "--base-url", "-b"),
    noto: Optional[str] = typer.Option(None, "--noto", "-n"),
    modelo: Optional[str] = typer.Option(None, "--modelo", "-m"),
) -> None:
    """[DEPRECATED] Use 'agordi aldoni' instead."""
    warning(tr_multi("'agordo sxlosilo' estas eksdata. Uzu 'agordi aldoni'.", "'agordo sxlosilo' is deprecated. Use 'agordi aldoni'.", "'agordo sxlosilo' est obsolète. Utilisez 'agordi aldoni'."))
    aldoni(provizanto, key=key, base_url=base_url, noto=noto, modelo=modelo)


# ── default — set default provider (sets prioritato=0) ────────────────────


@agordo_app.command("default", help=tr_multi(
    "Agordi la implicitan LLM-provizanton", "Set the default LLM provider", "Configurer le fournisseur LLM par defaut",
))
def default(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi("Provizanto (huggingface/deepseek/openai/ollama)", "Provider (huggingface/deepseek/openai/ollama)", "Fournisseur (huggingface/deepseek/openai/ollama)"),
    ),
) -> None:
    """Set the default LLM provider by setting its priority to 0 (highest)."""
    _validate_provider(provizanto)
    # Find config for this provider
    config = find_config(provizanto)
    if not config:
        warning(tr_multi(
            f"Provizanto '{provizanto}' ne estas agordita. Uzu 'agordi aldoni' unue.",
            f"Provider '{provizanto}' is not configured. Use 'agordi aldoni' first.",
            f"Le fournisseur '{provizanto}' n'est pas configuré. Utilisez d'abord 'agordi aldoni'.",
        ))
        raise typer.Exit(1)

    # Set prioritato=0 for this provider, shift others by +1
    from A_agento.data.provider_config import get_db as _get_db
    db = _get_db()
    db.execute("UPDATE provizanto_agordoj SET prioritato = prioritato + 1 WHERE provider != ? OR profile != ?",
               (config["provider"], config.get("profile", "default")))
    db.execute("UPDATE provizanto_agordoj SET prioritato = 0 WHERE uuid = ?", (config["uuid"],))
    success(tr_multi(
        f"Implicitita provizanto: {provizanto} (prioritato 0)",
        f"Default provider: {provizanto} (priority 0)",
        f"Fournisseur par défaut: {provizanto} (priorité 0)",
    ))


# ── ls — list all providers ────────────────────────────────────────────────


@agordo_app.command("ls", help=tr_multi(
    "Montri nunan agordon de provizantoj", "Show current provider configuration", "Afficher la configuration actuelle du fournisseur",
))
def agordo_ls() -> None:
    """Show current provider configuration in fallback order."""
    from rich.console import Console
    from rich.table import Table
    from A_agento.provider_state import get_fallback_order

    console = Console()
    fallback = get_fallback_order()
    if fallback:
        info(tr_multi(
            f"Falorodo: {' > '.join(fallback)}",
            f"Fallback order: {' > '.join(fallback)}",
            f"Ordre de secours: {' > '.join(fallback)}",
        ))
    else:
        info(tr_multi(
            "Neniuj provizantoj agorditaj. Uzu 'agordi aldoni' por aldoni ŝlosilon.",
            "No providers configured. Use 'agordi aldoni' to add a key.",
            "Aucun fournisseur configuré. Utilisez 'agordi aldoni' pour ajouter une clé.",
        ))
        return

    configs = list_provider_configs()
    if not configs:
        return

    #
    # Greyscale-accessible palette: Prior. (red = emphasis),
    # all others use default (white) for maximum readability.
    # Avoid dim/blue/magenta — they are near-invisible in grayscale.
    #
    table = Table(title=tr_multi('Provizantoj', 'Providers', 'Fournisseurs'))
    table.add_column(tr_multi('Prior.', 'Pri.', 'Pri.'), style="red", no_wrap=True)
    table.add_column(tr_multi('UUID', 'UUID', 'UUID'))
    table.add_column(tr_multi('Provizanto', 'Provider', 'Fournisseur'))
    table.add_column(tr_multi('Profilon', 'Profile', 'Profil'))
    table.add_column(tr_multi("Sxlosilo", "Key", "Cle"))
    table.add_column(tr_multi('Modelo', 'Model', 'Modele'))
    table.add_column(tr_multi('Baza URL', 'Base URL', 'URL de base'))
    table.add_column(tr_multi('Etikedo', 'Label', 'Etiquette'))

    for cfg in configs:
        prov = cfg["provider"]
        prof = cfg.get("profile", "default")
        prio = cfg.get("prioritato", 0)
        api_key = get_api_key(provider=prov, profile=prof)
        masked = ("..." + api_key[-4:]) if api_key else tr_multi("mankas", "missing", "manquant")
        entry_uuid = cfg.get("uuid", "")[:8] or "-"
        table.add_row(str(prio), entry_uuid, prov, prof, masked,
                       cfg.get("modelo", "") or "-", cfg.get("base_url", "") or "-", cfg.get("noto", "") or "-")

    console.print(table)


@agordo_app.command("montri", hidden=True)
def montri() -> None:
    """[DEPRECATED] Use 'agordi ls' instead."""
    agordo_ls()


# ── testi — test provider connectivity ────────────────────────────────────


@agordo_app.command("testi", help=tr_multi(
    "Testi konekton al provizanto", "Test provider connectivity", "Tester la connexion au fournisseur",
))
def testi(
    provizanto: Optional[str] = typer.Option(
        None, "--provizanto", "-P",
        help=tr_multi("Provizanto por testi (implicitite: unua en falorodo)", "Provider to test (default: first in fallback order)", "Fournisseur à tester (défaut: premier dans l'ordre de secours)"),
    ),
) -> None:
    """Test provider connectivity with a minimal prompt."""
    provider = _get_provider_for_test(provizanto)
    info(tr_multi(f"Testas {provider.name}...", f"Testing {provider.name}...", f"Test de {provider.name}..."))
    try:
        result = provider.generate("Reply with exactly one word: OK")
        clean = result.strip().lower().rstrip(".,!?;:")
        if "ok" in clean:
            success(tr_multi(f"{provider.name} respondis sukcese.", f"{provider.name} responded successfully.", f"{provider.name} a répondu avec succès."))
        else:
            warning(tr_multi(f"{provider.name} respondis sed neatendite: {result[:80]}", f"{provider.name} responded but unexpected: {result[:80]}", f"{provider.name} a répondu mais de façon inattendue: {result[:80]}"))
    except Exception as e:
        error(tr_multi(f"{provider.name} eraro: {e}", f"{provider.name} error: {e}", f"{provider.name} erreur: {e}"))
        raise typer.Exit(1) from e


__all__ = [
    "agordo_app",
]
