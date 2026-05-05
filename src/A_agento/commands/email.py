"""A-agento AI commands for email (A-lien integration).

Functions:
- resumu: Summarize recent emails
- respondi: Generate smart reply draft
- agu: Extract actions from email
"""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error, success
from A_agento.commands._helpers import get_provider_or_exit, confirm_action


def resumu(
    limit: int = typer.Option(
        10,
        "--limo",
        "-l",
        help=tr_multi(
            "Maksimumo da retposxtoj",  # eo
            "Maximum emails",  # en
            "Nombre maximum d'emails",  # fr
        ),
    ),
    nur_ne_legitaj: bool = typer.Option(
        True,
        "--nur-ne-legitaj",
        "-n",
        help=tr_multi(
            "Nur ne legitaj retposxtoj",  # eo
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
    """Summarize recent emails using AI.

    Examples:
        agento resumu
        agento resumu --limo 5 --nur-ne-legitaj
    """
    from rich.console import Console
    from rich.table import Table

    from A_agento.service import get_agent_service
    from A_agento.data import add_history

    provider = get_provider_or_exit(provizanto)
    agent = get_agent_service()

    info(tr_multi(
        "Sxargas retposxtojn...",  # eo
        "Loading emails...",  # en
        "Chargement des emails...",  # fr
    ))

    summaries = agent.summarize_emails(
        provider,
        limit=limit,
        unread_only=nur_ne_legitaj,
    )

    if not summaries:
        info(tr("Neniuj retposxtoj por resumi."))  # No emails to summarize
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


def respondi(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Retposxta UUID",  # eo
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
    from A_agento.service import get_agent_service
    from A_agento.data import add_history

    provider = get_provider_or_exit(provizanto)
    agent = get_agent_service()

    info(tr_multi(
        "Generadas respondon...",  # eo
        "Generating reply...",  # en
        "Generation de la reponse...",  # fr
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


def agu(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Retposxta UUID",  # eo
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

    Uses AI to parse an email and suggest actions: calendar events,
    todo items, or knowledge entries.

    Examples:
        agento agu abc-123
    """
    from rich.console import Console
    from rich.table import Table

    from A_agento.service import get_agent_service

    provider = get_provider_or_exit(provizanto)
    agent = get_agent_service()

    info(tr_multi(
        "Analizas retposxton...",  # eo
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
        # Allow user to edit before confirmation
        info(tr("Vi povas redakti antaux konfirmo. premu Enter por konservi."))

        if action.action_type == "calendar":
            new_title = typer.prompt(
                tr("Titolo"),  # Title
                default=action.metadata.get("title", action.title),
            )
            new_start = typer.prompt(
                tr("Komenco (ISO+Z)"),  # Start (ISO+Z)
                default=action.metadata.get("start", ""),
            )
            new_end = typer.prompt(
                tr("Fino (ISO+Z)"),  # End (ISO+Z)
                default=action.metadata.get("end", ""),
            )
            new_location = typer.prompt(
                tr("Loko"),  # Location
                default=action.metadata.get("location", ""),
            )
            new_ripeto = typer.prompt(
                tr("Ripeto (FREQ=...)"),  # Recurrence
                default=action.metadata.get("ripeto", ""),
            )
            new_remind = typer.prompt(
                tr("Memorigu (15m/1h/1d)"),  # Reminder
                default=action.metadata.get("remind", ""),
            )
            new_desc = typer.prompt(
                tr("Priskribo"),  # Description
                default=action.metadata.get("description", action.details),
            )

            action.metadata["title"] = new_title
            action.metadata["start"] = new_start
            action.metadata["end"] = new_end
            action.metadata["location"] = new_location
            action.metadata["ripeto"] = new_ripeto
            action.metadata["remind"] = new_remind
            action.metadata["description"] = new_desc
            action.title = new_title

            details_parts = [f"{new_start} -> {new_end}"]
            if new_location:
                details_parts.append(f"loko: {new_location}")
            if new_ripeto:
                details_parts.append(f"ripeto: {new_ripeto}")
            if new_remind:
                details_parts.append(f"memorigu: {new_remind}")
            action.details = ", ".join(details_parts)

            confirm_msg = f"kalend: {new_title} ({new_start} -> {new_end})"

        elif action.action_type == "todo":
            new_title = typer.prompt(
                tr("Titolo"),  # Title
                default=action.metadata.get("title", action.title),
            )
            new_due = typer.prompt(
                tr("Limdato (ISO+Z)"),  # Due date (ISO+Z)
                default=action.metadata.get("due", ""),
            )
            new_priority = typer.prompt(
                tr("Prioritato"),  # Priority
                default=action.metadata.get("priority", "normal"),
            )
            new_desc = typer.prompt(
                tr("Priskribo"),  # Description
                default=action.metadata.get("description", action.details),
            )

            action.metadata["title"] = new_title
            action.metadata["due"] = new_due
            action.metadata["priority"] = new_priority
            action.metadata["description"] = new_desc
            action.title = new_title
            action.details = f"due: {new_due}, priority: {new_priority}"

            confirm_msg = f"todo: {new_title} (due: {new_due})"

        else:
            # Knowledge: edit title, content, ligilo, superklaso
            new_title = typer.prompt(
                tr("Titolo"),  # Title
                default=action.title,
            )
            new_content = typer.prompt(
                tr("Enhavo"),  # Content
                default=action.details,
            )
            new_ligilo = typer.prompt(
                tr("Ligilo (UUID-kompostaj)"),  # Links (comma-separated UUIDs)
                default=",".join(action.metadata.get("ligilo", [])),
            )
            new_superklaso = typer.prompt(
                tr("Superklaso (UUID-kompostaj)"),  # Parent categories
                default=",".join(action.metadata.get("superklaso", [])),
            )

            action.title = new_title
            action.details = new_content
            action.metadata["title"] = new_title
            action.metadata["content"] = new_content
            action.metadata["ligilo"] = [
                x.strip() for x in new_ligilo.split(",") if x.strip()
            ]
            action.metadata["superklaso"] = [
                x.strip() for x in new_superklaso.split(",") if x.strip()
            ]
            confirm_msg = f"knowledge: {new_title}"

        if confirm_action(confirm_msg):
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


__all__ = [
    "resumu",
    "respondi",
    "agu",
]
