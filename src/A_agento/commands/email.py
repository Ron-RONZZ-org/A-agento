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
            "Maksimumo da retpostoj",  # eo
            "Maximum emails",  # en
            "Nombre maximum d'emails",  # fr
        ),
    ),
    nur_ne_legitaj: bool = typer.Option(
        True,
        "--nur-ne-legitaj",
        "-n",
        help=tr_multi(
            "Nur ne legitaj retpostoj",  # eo
            "Only unread emails",  # en
            "Uniquement les emails non lus",  # fr
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "Provizanto, provizanto:profilon, aux UUID. Vidu 'agento agordi ls' por listo.",  # eo
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",  # en
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",  # fr
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
        "Sargas retpostojn...",  # eo
        "Loading emails...",  # en
        "Chargement des emails...",  # fr
    ))

    summaries = agent.summarize_emails(
        provider,
        limit=limit,
        unread_only=nur_ne_legitaj,
    )

    if not summaries:
        info(tr_multi('Neniuj retpostoj por resumi.', 'No emails to summarize.', 'Aucun email a resumer.'))  # No emails to summarize
        return

    # Display summaries
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column(tr_multi('Subjekto', 'Subject', 'Sujet'))  # Subject
    table.add_column(tr_multi('Sendinto', 'From', 'De'))  # From
    table.add_column(tr_multi('Resumo', 'Summary', 'Resume'))  # Summary

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

    success(tr_multi('Finita.', 'Done.', 'Fini.'))  # Done


def respondi(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Retposta UUID",  # eo
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
            "Provizanto, provizanto:profilon, aux UUID. Vidu 'agento agordi ls' por listo.",  # eo
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",  # en
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",  # fr
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
        error(tr_multi('Ne povis generi respondon.', 'Could not generate reply.', 'Impossible de generer la reponse.'))  # Could not generate reply
        raise typer.Exit(1)

    info(tr_multi('Respondo:', 'Reply:', 'Reponse :'))  # Reply:
    print("\n" + reply + "\n")  # TODO: use info()

    # Save to history
    add_history(
        uuid=uuid,
        tipo="respondo",
        prompto=f"Reply to email {uuid}",
        respondon=reply,
        model=provider.model,
        provizanto=provider.name,
    )

    success(tr_multi('Finita.', 'Done.', 'Fini.'))  # Done


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
            "Provizanto, provizanto:profilon, aux UUID. Vidu 'agento agordi ls' por listo.",  # eo
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",  # en
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",  # fr
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
        "Analizas retposton...",  # eo
        "Analyzing email...",  # en
        "Analyse de l'email...",  # fr
    ))

    actions = agent.extract_actions(provider, uuid)

    if not actions:
        info(tr_multi('Neniuj agoj trovitaj.', 'No actions found.', 'Aucune action trouvee.'))  # No actions found
        return

    # Display actions
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column(tr_multi('Tipo', 'Type', 'Type'))  # Type
    table.add_column(tr_multi('Titolo', 'Title', 'Titre'))  # Title
    table.add_column(tr_multi('Detaloj', 'Details', 'Details'))  # Details

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
        info(tr_multi('Vi povas redakti antaux konfirmo. premu Enter por konservi.', 'You can edit before confirming. Press Enter to keep.', 'Vous pouvez modifier avant de confirmer. Appuyez sur Enter pour conserver.'))

        if action.action_type == "calendar":
            new_title = typer.prompt(
                tr_multi('Titolo', 'Title', 'Titre'),  # Title
                default=action.metadata.get("title", action.title),
            )
            new_start = typer.prompt(
                tr_multi('Komenco (ISO+Z)', 'Start (ISO+Z)', 'Debut (ISO+Z)'),  # Start (ISO+Z)
                default=action.metadata.get("start", ""),
            )
            new_end = typer.prompt(
                tr_multi('Fino (ISO+Z)', 'End (ISO+Z)', 'Fin (ISO+Z)'),  # End (ISO+Z)
                default=action.metadata.get("end", ""),
            )
            new_location = typer.prompt(
                tr_multi('Loko', 'Location', 'Emplacement'),  # Location
                default=action.metadata.get("location", ""),
            )
            new_ripeto = typer.prompt(
                tr_multi('Ripeto (FREQ=...)', 'Recurrence (FREQ=...)', 'Recurrence (FREQ=...)'),  # Recurrence
                default=action.metadata.get("ripeto", ""),
            )
            new_remind = typer.prompt(
                tr_multi('Memorigu (15m/1h/1d)', 'Reminder (15m/1h/1d)', 'Rappel (15m/1h/1d)'),  # Reminder
                default=action.metadata.get("remind", ""),
            )
            new_desc = typer.prompt(
                tr_multi('Priskribo', 'Description', 'Description'),  # Description
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
                tr_multi('Titolo', 'Title', 'Titre'),  # Title
                default=action.metadata.get("title", action.title),
            )
            new_due = typer.prompt(
                tr_multi('Limdato (ISO+Z)', 'Due date (ISO+Z)', 'Date limite (ISO+Z)'),  # Due date (ISO+Z)
                default=action.metadata.get("due", ""),
            )
            new_priority = typer.prompt(
                tr_multi('Prioritato', 'Priority', 'Priorite'),  # Priority
                default=action.metadata.get("priority", "normal"),
            )
            new_desc = typer.prompt(
                tr_multi('Priskribo', 'Description', 'Description'),  # Description
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
                tr_multi('Titolo', 'Title', 'Titre'),  # Title
                default=action.title,
            )
            new_content = typer.prompt(
                tr_multi('Enhavo', 'Content', 'Contenu'),  # Content
                default=action.details,
            )
            new_ligilo = typer.prompt(
                tr_multi('Ligilo (UUID-kompostaj)', 'Links (comma-separated UUIDs)', 'Liens (UUID separes par virgules)'),  # Links (comma-separated UUIDs)
                default=",".join(action.metadata.get("ligilo", [])),
            )
            new_superklaso = typer.prompt(
                tr_multi('Superklaso (UUID-kompostaj)', 'Parent categories (comma-separated UUIDs)', 'Categories parentes (UUID separes par virgules)'),  # Parent categories
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
                    success(tr_multi('Kreita okazis.', 'Created event.', 'Evenement cree.'))  # Created event

            elif action.action_type == "todo":
                result = agent.create_todo(action.metadata)
                if result:
                    success(tr_multi('Kreita tasko.', 'Created task.', 'Tache creee.'))  # Created task

            elif action.action_type == "knowledge":
                result = agent.create_knowledge_entry(action.metadata)
                if result:
                    success(tr_multi('Kreita sciento.', 'Created knowledge.', 'Connaissance creee.'))  # Created knowledge

        else:
            info(tr_multi('Nuligita.', 'Cancelled.', 'Annule.'))  # Cancelled


__all__ = [
    "resumu",
    "respondi",
    "agu",
]
