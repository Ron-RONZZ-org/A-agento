"""A-agento AI commands for knowledge (A-encik integration).

Functions:
- generi: Generate knowledge entry with AI
"""

from __future__ import annotations

from typing import Optional

import typer

from A import tr, tr_multi, info, error, success
from A_agento.commands._helpers import get_provider_or_exit


def generi(
    prompto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Temo au priskribo por la enhavo",  # eo
            "Topic or description for the content",  # en
            "Sujet ou description du contenu",  # fr
        ),
    ),
    titolo: Optional[str] = typer.Option(
        None,
        "--titolo",
        "-t",
        help=tr_multi(
            "Titolo (au autogenerita se ne donita)",  # eo
            "Title (auto-generated if omitted)",  # en
            "Titre (auto-genere si omis)",  # fr
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
    konservi: bool = typer.Option(
        False,
        "--konservi",
        "-k",
        help=tr_multi(
            "Konservi la rezulton en A-encik",  # eo
            "Save the result to A-encik",  # en
            "Enregistrer le resultat dans A-encik",  # fr
        ),
    ),
) -> None:
    """Generate content with AI.

    Uses the configured LLM provider to generate content based on a
    topic or description. Optionally saves the result as a knowledge
    entry in A-encik if that module is installed.

    Examples:
        agento generi "Explain quantum computing in simple terms"
        agento generi "Meeting notes template" --titolo "Notes" --konservi
    """
    provider = get_provider_or_exit(provizanto)

    info(tr_multi(
        "Generas enhavon...",  # eo
        "Generating content...",  # en
        "Generation du contenu...",  # fr
    ))

    prompt = (
        f"You are a helpful writing assistant.\n"
        f"Generate well-structured content on the following topic.\n"
        f"{'Title: ' + titolo if titolo else ''}\n\n"
        f"Topic: {prompto}\n\n"
        f"Content:"
    )

    try:
        content = provider.generate(prompt)
    except Exception as e:
        error(
            tr_multi(
                f"Generado malsukcesis: {e}",  # eo
                f"Generation failed: {e}",  # en
                f"Generation echouee: {e}",  # fr
            )
        )
        raise typer.Exit(1) from e

    if not content or not content.strip():
        error(
            tr_multi(
                "Neniu enhavo generita.",  # eo
                "No content generated.",  # en
                "Aucun contenu genere.",  # fr
            )
        )
        raise typer.Exit(1)

    # Display result
    title_display = titolo or prompto[:40]
    print(f"\n[ {title_display} ]\n")
    print(content.strip())
    print()

    success(
        tr_multi(
            "Enhavo generita sukcese.",  # eo
            "Content generated successfully.",  # en
            "Contenu genere avec succes.",  # fr
        )
    )

    # Optionally save to A-encik
    if konservi:
        _save_to_encik(titolo or prompto, content)


def _save_to_encik(title: str, content: str) -> None:
    """Save generated content to A-encik if available.

    Args:
        title: Entry title
        content: Generated content body
    """
    try:
        from A_encik.service import get_service

        service = get_service()
        entry = service.create({
            "titolo": title,
            "enhavo": content,
        })
        if entry:
            success(
                tr_multi(
                    f"Konservita en A-encik: {title}",  # eo
                    f"Saved to A-encik: {title}",  # en
                    f"Enregistre dans A-encik: {title}",  # fr
                )
            )
    except ImportError:
        info(
            tr_multi(
                "A-encik ne estas instalita. Rezulto ne konservita.",  # eo
                "A-encik is not installed. Result not saved.",  # en
                "A-encik n'est pas installe. Resultat non enregistre.",  # fr
            )
        )
    except Exception as e:
        error(
            tr_multi(
                f"Ne povis konservi en A-encik: {e}",  # eo
                f"Could not save to A-encik: {e}",  # en
                f"Impossible d'enregistrer dans A-encik: {e}",  # fr
            )
        )


__all__ = [
    "generi",
]
