"""CLI for A-agento — AI email agent.

Commands:
- resumu: Summarize recent emails
- respondu: Generate smart reply draft
- agu: Extract actions from email
"""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error, success
from A.core.ai import get_provider, set_default_provider, get_default_provider

# Import services
from A_agento.service import get_agent_service, EmailSummary, ActionSuggestion
from A_agento.data import add_history

app = typer.Typer(
    name="agento",
    help=tr_multi(
        "A-agento — AI retpoŝta agento kun LLM",  # eo
        "A-agento — AI email agent with LLM",  # en
        "A-agento — Agent email IA avec LLM",  # fr
    ),
)


def _get_provider(
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


def _confirm_action(description: str) -> bool:
    """Show action preview and ask user to confirm.

    Args:
        description: Action description

    Returns:
        True if confirmed
    """
    info(f"Proponita ago: {description}")
    return typer.confirm(tr_multi("Ĉu plenumi?", "Execute?", "Exécuter?"))


# --- Commands ---


@app.command("resumu")
def resumu(
    limit: int = typer.Option(
        10,
        "--limo",
        "-l",
        help=tr_multi(
            "Maksimumo da retpoŝtoj",  # eo
            "Maximum emails",  # en
            "Nombre maximum d'emails",  # fr
        ),
    ),
    nur_ne_legitaj: bool = typer.Option(
        True,
        "--nur-ne-legitaj",
        "-n",
        help=tr_multi(
            "Nur ne legitaj retpoŝtoj",  # eo
            "Only unread emails",  # en
            "Uniquement les emails non lus",  # fr
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "LLM provizanto (openai/ollama/auto)",  # eo
            "LLM provider (openai/ollama/auto)",  # en
            "Fournisseur LLM (openai/ollama/auto)",  # fr
        ),
    ),
) -> None:
    """Summarize recent emails.

    Examples:
        agento resumu
        agento resumo --limo 5 --nur-ne-legitaj
    """
    from rich.console import Console
    from rich.table import Table

    provider = _get_provider(provizanto)
    agent = get_agent_service()

    info(tr_multi(
        "Ŝarĝas retpoŝtojn...",  # eo
        "Loading emails...",  # en
        "Chargement des emails...",  # fr
    ))

    summaries = agent.summarize_emails(
        provider,
        limit=limit,
        unread_only=nur_ne_legitaj,
    )

    if not summaries:
        info(tr("Neniuj retpoŝtoj por resumi."))  # No emails to summarize
        return

    # Display summaries
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column(tr("Subjekto"))  # Subject
    table.add_column(tr("Sendinto"))  # From
    table.add_column(tr("Resumo"))  # Summary

    for i, summary in enumerate(summaries, 1):
        table.add_row(
            str(i),
            summary.subject[:40],
            summary.sender[:20],
            summary.summary[:60],
        )

    console.print(table)

    # Log to history
    for summary in summaries:
        add_history(
            uuid=summary.uuid,
            tipo="resumo",
            prompto=f"From: {summary.sender}\nSubject: {summary.subject}",
            respondon=summary.summary,
            model=provider.model,
            provizanto=provider.name,
        )

    success(tr("Finita."))  # Done


@app.command("respondu")
def respondu(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Retpoŝta UUID",  # eo
            "Email UUID",  # en
            "UUID de l'email",  # fr
        ),
    ),
    tono: str = typer.Option(
        "courteous",
        "--tono",
        "-t",
        help=tr_multi(
            "Tono (courteous/casual/formal)",  # eo
            "Tone (courteous/casual/formal)",  # en
            "Ton (courteous/casual/formal)",  # fr
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "LLM provizanto",  # eo
            "LLM provider",  # en
            "Fournisseur LLM",  # fr
        ),
    ),
) -> None:
    """Generate a smart reply draft for an email.

    Examples:
        agento respondu abc-123
        agento respondu abc-123 --tono casual
    """
    provider = _get_provider(provizanto)
    agent = get_agent_service()

    info(tr_multi(
        "Ĝeneradas respondon...",  # eo
        "Generating reply...",  # en
        "Génération de la réponse...",  # fr
    ))

    reply = agent.generate_reply(provider, uuid, tone=tono)

    if not reply:
        error(tr("Ne povis generi respondon."))  # Could not generate reply
        raise typer.Exit(1)

    info(tr("Respondo:"))  # Reply:
    print("\n" + reply + "\n")

    # Save to history
    add_history(
        uuid=uuid,
        tipo="respondo",
        prompto=f"Reply to email {uuid}",
        respondon=reply,
        model=provider.model,
        provizanto=provider.name,
    )

    success(tr("Finita."))  # Done


@app.command("agu")
def agu(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Retpoŝta UUID",  # eo
            "Email UUID",  # en
            "UUID de l'email",  # fr
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "LLM provizanto",  # eo
            "LLM provider",  # en
            "Fournisseur LLM",  # fr
        ),
    ),
) -> None:
    """Extract actions from an email (calendar, todo, knowledge).

    Examples:
        agento agu abc-123
    """
    from rich.console import Console
    from rich.table import Table

    provider = _get_provider(provizanto)
    agent = get_agent_service()

    info(tr_multi(
        "Analizas retpoŝton...",  # eo
        "Analyzing email...",  # en
        "Analyse de l'email...",  # fr
    ))

    actions = agent.extract_actions(provider, uuid)

    if not actions:
        info(tr("Neniuj agoj trovitaj."))  # No actions found
        return

    # Display actions
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column(tr("Tipo"))  # Type
    table.add_column(tr("Titolo"))  # Title
    table.add_column(tr("Detaloj"))  # Details

    for action in actions:
        table.add_row(
            action.action_type,
            action.title[:40],
            action.details[:40],
        )

    console.print(table)

    # Confirm and execute each action
    for action in actions:
        if _confirm_action(f"{action.action_type}: {action.title}"):
            if action.action_type == "calendar":
                result = agent.create_calendar_event(action.metadata)
                if result:
                    success(tr("Kreita okazis."))  # Created event

            elif action.action_type == "todo":
                result = agent.create_todo(action.metadata)
                if result:
                    success(tr("Kreita tasko."))  # Created task

            elif action.action_type == "knowledge":
                result = agent.create_knowledge_entry(action.metadata)
                if result:
                    success(tr("Kreita sciento."))  # Created knowledge

        else:
            info(tr("Nuligita."))  # Cancelled


@app.command("agordo")
def agordo(
    provizanto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Provizanto (openai/ollama)",  # eo
            "Provider (openai/ollama)",  # en
            "Fournisseur (openai/ollama)",  # fr
        ),
    ),
) -> None:
    """Set default LLM provider.

    Examples:
        agento agordo ollama
        agento agordo openai
    """
    try:
        set_default_provider(provizanto)
        success(tr("Ĝisdatigita."))  # Updated
    except ValueError as e:
        error(str(e))
        raise typer.Exit(1) from e


# Make module callable as CLI
if __name__ == "__main__":
    app()