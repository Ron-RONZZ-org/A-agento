"""A-agento stilo — writing style sample management commands.

Sub-app for the `stilo` command group and related list/delete/activate commands.
"""

from __future__ import annotations

import uuid

import typer

from A import tr, tr_multi, info, error, success
from A_agento.data.storage import (
    add_style_sample,
    list_style_samples,
    delete_style_sample,
    set_sample_active,
)

stilo_app = typer.Typer(
    name="stilo",
    help=tr_multi(
        "Administri skribstilajn specimojn",  # eo
        "Manage writing style samples",  # en
        "Gérer les échantillons de style d'écriture",  # fr
    ),
    no_args_is_help=True,
)


@stilo_app.command("aldoni", help=tr_multi(
    "Registri skribstilan specimon",  # eo
    "Register a writing style sample",  # en
    "Enregistrer un echantillon de style d'ecriture",  # fr
))
def aldoni(
    substilo: str = typer.Argument(
        ...,
        help=tr_multi(
            "Specimo-tipo (reply/summary)",  # eo
            "Sample type (reply/summary)",  # en
            "Type d'échantillon (reply/summary)",  # fr
        ),
    ),
    enhavo: str = typer.Argument(
        ...,
        help=tr_multi(
            "Teksto de la specimo",  # eo
            "Sample text",  # en
            "Texte de l'échantillon",  # fr
        ),
    ),
) -> None:
    """Register a user writing style sample.

    Examples:
        agento stilo aldoni reply "Sure, let's sync up next week."
        agento stilo aldoni summary "Quick update: project on track."
    """
    valid_types = ("reply", "summary")
    if substilo not in valid_types:
        error(tr_multi(f"Nevalida tipo. Uzu: {', '.join(valid_types)}", f"Invalid type. Use: {', '.join(valid_types)}", f"Type invalide. Utilisez : {', '.join(valid_types)}"))
        raise typer.Exit(1)

    sample_uuid = str(uuid.uuid4())[:8]
    add_style_sample(
        uuid=sample_uuid,
        sample_type=substilo,
        content=enhavo,
    )
    success(tr_multi('Specimo aldonita.', 'Sample added.', 'Echantillon ajoute.'))  # Sample added


@stilo_app.command("ls", help=tr_multi(
    "Listi registritajn stilajn specimojn",  # eo
    "List registered style samples",  # en
    "Lister les echantillons de style enregistres",  # fr
))
def stilo_ls() -> None:
    """List registered style samples."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    samples = list_style_samples()

    if not samples:
        info(tr_multi('Neniuj specimoj.', 'No samples.', 'Aucun echantillon.'))  # No samples
        return

    table = Table(title=tr_multi('Stilo-specimoj', 'Style samples', 'Echantillons de style'))
    table.add_column("UUID", style="cyan")
    table.add_column("Tipo", style="magenta")
    table.add_column("Enhavo", style="white")
    table.add_column("Aktiva", style="green")

    for s in samples:
        table.add_row(
            s["uuid"],
            s["sample_type"],
            s["content"][:50] + "..." if len(s["content"]) > 50 else s["content"],
            "\u2713" if s["active"] else "\u2717",
        )

    console.print(table)


@stilo_app.command("listo", hidden=True)
def listo() -> None:
    """[DEPRECATED] Use 'stilo ls' instead."""
    stilo_ls()


@stilo_app.command("forigi", help=tr_multi(
    "Forigi skribstilan specimon",  # eo
    "Remove a style sample",  # en
    "Supprimer un echantillon de style",  # fr
))
def forigi(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Specimo UUID",  # eo
            "Sample UUID",  # en
            "UUID de l'échantillon",  # fr
        ),
    ),
) -> None:
    """Remove a style sample."""
    delete_style_sample(uuid)
    success(tr_multi('Specimo forigita.', 'Sample deleted.', 'Echantillon supprime.'))  # Sample deleted


@stilo_app.command("forigu", hidden=True)
def forigu(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Specimo UUID",  # eo
            "Sample UUID",  # en
            "UUID de l'échantillon",  # fr
        ),
    ),
) -> None:
    """[DEPRECATED] Use 'stilo forigi' instead."""
    forigi(uuid)


@stilo_app.command("aktiva", help=tr_multi(
    "Aktivigi aux malaktivigi specimon",  # eo
    "Activate or deactivate a sample",  # en
    "Activer ou desactiver un echantillon",  # fr
))
def aktiva(
    uuid: str = typer.Argument(
        ...,
        help=tr_multi(
            "Specimena UUID",  # eo
            "Sample UUID",  # en
            "UUID exemple",  # fr
        ),
    ),
    activa: bool = typer.Option(
        True,
        "--aktiva/--malaktiva",
        help=tr_multi(
            "Aktivigi aŭ malaktivigi",  # eo
            "Activate or deactivate",  # en
            "Activer ou désactiver",  # fr
        ),
    ),
) -> None:
    """Activate or deactivate a style sample."""
    set_sample_active(uuid, activa)
    status_text = "aktiva" if activa else "malaktiva"
    success(
        tr_multi(
            f"Specimo {status_text}.",  # eo
            f"Sample {status_text}.",  # en
            f"Échantillon {status_text}.",  # fr
        )
    )


__all__ = [
    "stilo_app",
]
