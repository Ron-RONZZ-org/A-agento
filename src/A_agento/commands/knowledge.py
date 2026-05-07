"""A-agento AI commands for text generation.

Functions:
- generi: Generate content with AI (txt, md, json, enc formats)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success
from A_agento.commands._helpers import get_provider_or_exit
from A_agento.tools import generate_with_tools, ENCIK_TOOLS
from A_agento.prompt_loader import load_prompt


# ── Format-specific prompt builders ──────────────────────────────────────────


def _get_format_prompt(formato: str) -> str:
    """Load a format prompt with three-tier fallback.

    1. ~/.config/A/agento/prompts/generi_<formato>.prompt (user override)
    2. src/A_agento/prompts/generi_<formato>.prompt (packaged default)
    3. Embedded string (last resort)
    """
    return load_prompt(f"generi_{formato}")





def _looks_like_raw_json(content: str) -> bool:
    """Detect if content is raw JSON output from search_encik (not generated .enc)."""
    stripped = content.strip()
    if not stripped:
        return True  # Empty content is also a failure
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            data = json.loads(stripped)
            return isinstance(data, list)
        except (json.JSONDecodeError, TypeError):
            pass
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and "uuid" in data:
                return True  # Year creation result
        except (json.JSONDecodeError, TypeError):
            pass
    return False


def _clean_enc_output(content: str) -> str:
    """Clean up LLM-generated .enc content by stripping markdown artifacts.

    - Removes leading/trailing code fences (```enc, ```, ```toml, etc.)
    - Strips leading # title comments (tolerated by parser but not desired style)

    Args:
        content: Raw LLM output

    Returns:
        Cleaned .enc content

    Raises:
        ValueError: If content is raw JSON tool output, not generated content
    """
    import re

    # Safety net: reject raw JSON tool output
    if _looks_like_raw_json(content):
        raise ValueError("LLM returned raw tool output instead of generated content")

    # Strip leading and trailing code fences
    content = re.sub(r'^```\w*\s*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)

    # Strip leading # title comments (tolerated by parser but not desired style)
    lines = content.split('\n')
    while lines and lines[0].startswith('#') and not lines[0].startswith('##'):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)

    return '\n'.join(lines).strip()


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
            "Provizanto, provizanto:profilon, aux UUID. Vidu 'agento agordi ls' por listo.",  # eo
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",  # en
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",  # fr
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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "--detala",
        "-v",
        help=tr_multi(
            "Montri la plenan konversacion kun LLM (inkluzive de pensado)",  # eo
            "Show full LLM conversation (including reasoning/thinking)",  # en
            "Afficher la conversation complète avec LLM (y compris le raisonnement)",  # fr
        ),
    ),
    interjekti: bool = typer.Option(
        False,
        "--interjekti",
        "--interject",
        "-i",
        help=tr_multi(
            "Premu 'x' iam ajn por paŭzi kaj korekti. Uzu kun --detala.",  # eo
            "Press 'x' at any time to pause and type a correction. Use with --detala.",  # en
            "Appuyez sur 'x' à tout moment pour corriger. À utiliser avec --detala.",  # fr
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
    # Increase token limit for .enc generation (full entries with tool calls)
    if formato == "enc":
        provider._max_tokens = 4096
    title_line = f"Title: {titolo}" if titolo else ""

    info(tr_multi(
        f"Generas enhavon ({formato})...",  # eo
        f"Generating content ({formato})...",  # en
        f"Génération du contenu ({formato})...",  # fr
    ))

    try:
        prompt_text = _get_format_prompt(formato)
        if formato == "enc":
            prompt = prompt_text.format(title_line=title_line, prompto=prompto)
            messages = [{"role": "user", "content": prompt}]
            content = generate_with_tools(provider, messages, tools=ENCIK_TOOLS, verbose=verbose, interject=interjekti)
            content = _clean_enc_output(content)
        else:
            prompt = prompt_text.format(title_line=title_line, prompto=prompto)
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
    print()  # displayed content

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
