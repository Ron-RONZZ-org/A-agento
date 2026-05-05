"""A-agento AI command registration for cross-module injection.

Provides factory functions that create Typer sub-apps with AI commands
for each compatible A-module. These are registered as entry points
under the "A.ai_commands" group in pyproject.toml.

A-core's plugin loader discovers these entry points and injects the
AI sub-apps into the corresponding module's CLI on first use.
"""

from __future__ import annotations

import typer

from A import tr_multi

# Module-level cache for ai sub-apps
_AI_APPS_CACHE: dict[str, typer.Typer] = {}


def _make_ai_app(module: str, help_text: str) -> typer.Typer:
    """Create a cached Typer sub-app for AI commands.

    Args:
        module: Module identifier for cache key
        help_text: Help text for the sub-app

    Returns:
        Cached Typer instance
    """
    if module not in _AI_APPS_CACHE:
        _AI_APPS_CACHE[module] = typer.Typer(
            name="ai",
            help=help_text,
            no_args_is_help=True,
        )
    return _AI_APPS_CACHE[module]


def get_lien_ai_app() -> typer.Typer:
    """Get the AI sub-app for A-lien (email).

    Commands: resumu, respondi, agu

    Returns:
        Typer sub-app
    """
    from A_agento.commands.email import resumu, respondi, agu

    ai_app = _make_ai_app(
        "lien",
        tr_multi(
            "AI-funkcioj (per A-agento)",  # eo
            "AI functions (via A-agento)",  # en
            "Fonctions IA (via A-agento)",  # fr
        ),
    )

    ai_app.command(
        name="resumu",
        help=tr_multi(
            "Resumi retposxtojn kun AI",  # eo
            "Summarize emails with AI",  # en
            "Resumer les emails avec IA",  # fr
        ),
    )(resumu)
    ai_app.command(
        name="respondi",
        help=tr_multi(
            "Generi inteligentan respondon al retposxto",  # eo
            "Generate smart reply to an email",  # en
            "Generer une reponse intelligente a un email",  # fr
        ),
    )(respondi)
    ai_app.command(
        name="agu",
        help=tr_multi(
            "Elsxi agojn el retposxto",  # eo
            "Extract actions from an email",  # en
            "Extraire des actions d'un email",  # fr
        ),
    )(agu)

    return ai_app


def get_encik_ai_app() -> typer.Typer:
    """Get the AI sub-app for A-encik (knowledge).

    Commands: generi

    Returns:
        Typer sub-app
    """
    from A_agento.commands.knowledge import generi

    ai_app = _make_ai_app(
        "encik",
        tr_multi(
            "AI-funkcioj (per A-agento)",  # eo
            "AI functions (via A-agento)",  # en
            "Fonctions IA (via A-agento)",  # fr
        ),
    )

    ai_app.command(
        name="generi",
        help=tr_multi(
            "Generi enhavon kun AI",  # eo
            "Generate content with AI",  # en
            "Generer du contenu avec IA",  # fr
        ),
    )(generi)

    return ai_app


__all__ = [
    "get_lien_ai_app",
    "get_encik_ai_app",
]
