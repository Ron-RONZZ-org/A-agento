"""A-agento AI commands for text generation.

Functions:
- generi: Generate content with AI (txt, md, json, enc formats)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success
from A_agento.commands._helpers import get_provider_or_exit
from A_agento.tools import generate_with_tools, ENCIK_TOOLS


# ── Format-specific prompt builders ──────────────────────────────────────────

_FORMAT_PROMPTS = {
    "txt": """You are a helpful writing assistant.
Generate well-structured plain text content on the following topic.
{title_line}
Topic: {prompto}
Content:""",

    "md": """You are a helpful writing assistant.
Generate well-structured content in **Markdown** format with appropriate headers, lists, and formatting.
{title_line}
Topic: {prompto}
Content:""",

    "json": """You are a helpful writing assistant.
Generate the content as a **JSON object** with fields "title" and "content".
{title_line}
Topic: {prompto}
{"title": "...", "content": "..."}""",

    "enc": '''You are a knowledge entry generator for the encik personal knowledge base.

## .enc format rules

1. FILE STRUCTURE
   terminologio.{{lang}} = "term"        # required, one per language
   difino.{{lang}} = "short def"         # single-line definition
   difino.{{lang}} = """               # multi-line definition
   - point 1
   - point 2
   """
   # Optional display title comment

2. SYNTAX RULES
   - Identical terms: terminologio.(eo,fr,en)="Same Name" (literal, not a format parameter)
   - Links to existing entries: [display text](#uuid) or [title](#ec#uuid-prefix)
   - Semantic arcs: [value](#uuid, wdt:PROPERTY) (e.g. [1886](#e7a4692e, wdt:P571))
   - KaTeX formulas: $\\vec{{E}}=0$
   - Multi-section definitions: use ## for subsections
   - Keep formatting minimal, no extra explanation inside the .enc file

3. STYLE
   - Use markdown bullet points for definitions
   - Each point should be one concept
   - Use ## for major sections within difino
   - Reference existing entries by their UUIDs when linking

{title_line}
Topic: {prompto}
Generate only the .enc content, no extra explanation:''',
}


def _save_to_file(path: Path, content: str, titolo: str = "") -> None:
    """Save generated content to a file, showing confirmation.

    Args:
        path: Output file path
        content: Content to write
        titolo: Optional title for user feedback
    """
    if path.exists() and not typer.confirm(
        tr_multi(
            f"Dosiero {path} jam ekzistas. Anstataŭigi?",
            f"File {path} already exists. Overwrite?",
            f"Le fichier {path} existe déjà. Remplacer ?",
        ),
        default=False,
    ):
        info(tr_multi("Nuligita.", "Cancelled.", "Annulé."))
        return

    path.write_text(content, encoding="utf-8")
    success(
        tr_multi(
            f"Konservita al {path}",
            f"Saved to {path}",
            f"Enregistré dans {path}",
        )
    )


def generi(
    prompto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Temo au priskribo por la enhavo",  # eo
            "Topic or description for the content",  # en
            "Sujet ou description du contenu",  # fr
        ),
    ),
    formato: str = typer.Option(
        "txt",
        "--formato",
        "-f",
        help=tr_multi(
            "Formato (txt/md/json/enc)",  # eo
            "Format (txt/md/json/enc)",  # en
            "Format (txt/md/json/enc)",  # fr
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
    konservi: Optional[Path] = typer.Option(
        None,
        "--konservi",
        "-k",
        help=tr_multi(
            "Dosiero por konservi la rezulton (ekz: eligo.enc)",  # eo
            "File path to save the result (e.g. output.enc)",  # en
            "Chemin du fichier pour sauvegarder le resultat (ex: sortie.enc)",  # fr
        ),
    ),
) -> None:
    """Generate content with AI.

    Uses the configured LLM provider to generate content based on a
    topic or description. Supports multiple output formats:
    - txt: plain text
    - md: Markdown
    - json: structured JSON
    - enc: encik knowledge entry format (with DB lookup for links)

    If --konservi is given, saves to file for manual review.
    For .enc format, the AI can search your encik database for related
    entries to create proper links with real UUIDs.

    Examples:
        agento generi "Explain quantum computing"
        agento generi "macOS" --formato enc
        agento generi "Notes" --formato md --konservi notes.md
        agento generi "Python" --formato enc --konservi eligo.enc
    """
    valid_formats = ("txt", "md", "json", "enc")
    if formato not in valid_formats:
        error(
            tr_multi(
                f"Nevalida formato: {formato}. Validaj: {', '.join(valid_formats)}",  # eo
                f"Invalid format: {formato}. Valid: {', '.join(valid_formats)}",  # en
                f"Format invalide: {formato}. Valides: {', '.join(valid_formats)}",  # fr
            )
        )
        raise typer.Exit(1)

    provider = get_provider_or_exit(provizanto)
    title_line = f"Title: {titolo}" if titolo else ""

    info(tr_multi(
        f"Generas enhavon ({formato})...",  # eo
        f"Generating content ({formato})...",  # en
        f"Génération du contenu ({formato})...",  # fr
    ))

    try:
        if formato == "enc":
            prompt = _FORMAT_PROMPTS["enc"].format(title_line=title_line, prompto=prompto)
            messages = [{"role": "user", "content": prompt}]
            content = generate_with_tools(provider, messages, tools=ENCIK_TOOLS)
        else:
            prompt = _FORMAT_PROMPTS[formato].format(title_line=title_line, prompto=prompto)
            content = provider.generate(prompt)
    except Exception as e:
        error(
            tr_multi(
                f"Generado malsukcesis: {e}",  # eo
                f"Generation failed: {e}",  # en
                f"Génération échouée: {e}",  # fr
            )
        )
        raise typer.Exit(1) from e

    if not content or not content.strip():
        error(
            tr_multi(
                "Neniu enhavo generita.",  # eo
                "No content generated.",  # en
                "Aucun contenu généré.",  # fr
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
            "Contenu généré avec succès.",  # fr
        )
    )

    # Save to file if requested (human-in-the-loop: user reviews first)
    if konservi:
        _save_to_file(konservi, content.strip(), titolo or prompto)


__all__ = [
    "generi",
]
