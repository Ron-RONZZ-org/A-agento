"""A-agento enhancement command -- agento plibonigi.

Provides both a CLI command (plibonigi) and an importable function
(enhance_text) for use by other A-modules.

Exports:
    enhance_text(text, instruction, formato, provider_ref, context) -> str
    plibonigi()  -- Typer CLI command
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, warning, copy_to_clipboard
from A_agento.commands._context_helpers import (
    _core_html_to_text,
    _html_to_text,
    _truncate_context,
    _read_local_file,
    _offer_trafilatura_if_missing,
)
from A_agento.commands._knowledge_helpers import (
    _clean_enc_output,
    _save_to_file,
)
from A_agento.commands._enhancement_helpers import (
    enhance_text,
    _resolve_input_text,
    _infer_format_from_input,
)

_fetch_text = None
try:
    from A.core.http import fetch_text as _fetch_text
except ImportError:
    pass

_SUPPORTED_FORMATS = ("txt", "md", "json", "enc")


def plibonigi(
    input: str = typer.Argument(
        "",
        help=tr_multi(
            "Teksto au dosiervojo por plibonigi. Se ne donita, legas de tubo (stdin).",
            "Text or file path to enhance. If omitted, reads from pipe (stdin).",
            "Texte ou chemin de fichier a ameliorer. Si omis, lit depuis le pipe (stdin).",
        ),
    ),
    instruction: str = typer.Argument(
        "",
        help=tr_multi(
            "Instrukcioj por plibonigo (ekz: 'pli formala', 'aldonu ekzemplojn').",
            "Enhancement instructions (e.g. 'more formal', 'add examples').",
            "Instructions d'amelioration (ex: 'plus formel', 'ajoutez des exemples').",
        ),
    ),
    instrukcio_opt: Optional[str] = typer.Option(
        None,
        "--instrukcio",
        hidden=True,
        help=tr_multi(
            "Long-forma alternativo por instrukcioj (utila kiam enigo venas de tubo).",
            "Long-form alternative for instructions (useful when input comes from pipe).",
            "Alternative longue pour les instructions (utile quand l'entree vient d'un pipe).",
        ),
    ),
    formato: Optional[str] = typer.Option(
        None,
        "--formato",
        "-f",
        help=tr_multi(
            "Formato (txt/md/json/enc). Aûtomate detektita de dosier-sufikso se ne specifita.",
            "Format (txt/md/json/enc). Auto-detected from file extension if not specified.",
            "Format (txt/md/json/enc). Auto-detecte depuis l'extension du fichier si non specifie.",
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "Provizanto, provizanto:profilon, au UUID. Vidu 'agento agordi ls' por listo.",
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",
        ),
    ),
    konservi: Optional[Path] = typer.Option(
        None,
        "--konservi",
        "-K",
        help=tr_multi(
            "Dosiero por konservi la rezulton",
            "File path to save the result",
            "Chemin du fichier pour sauvegarder le resultat",
        ),
    ),
    kopii: bool = typer.Option(
        False,
        "--kopii",
        "-k",
        help=tr_multi(
            "Kopii la rezulton al tondujo",
            "Copy the result to clipboard",
            "Copier le resultat dans le presse-papiers",
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--detala",
        "--verbose", "-v", hidden=True,
        help=tr_multi(
            "Montri la plenan konversacion kun LLM",
            "Show full LLM conversation",
            "Afficher la conversation complete avec LLM",
        ),
    ),
    interjekti: bool = typer.Option(
        False,
        "--interjekti",
        "--interject",
        "-i",
        help=tr_multi(
            "Premu 'x' iam ajn por pauxzi kaj korekti. Uzu kun --detala.",
            "Press 'x' at any time to pause and type a correction. Use with --detala.",
            "Appuyez sur 'x' a tout moment pour corriger. A utiliser avec --detala.",
        ),
    ),
    ligilo: Optional[str] = typer.Option(
        None,
        "--ligilo",
        "-l",
        help=tr_multi(
            "URL de retpagho por kunteksto (LLM legos ghin)",
            "Web page URL to attach as context (LLM will read it)",
            "URL de page Web a attacher comme contexte (le LLM la lira)",
        ),
    ),
    dosiero: Optional[Path] = typer.Option(
        None,
        "--dosiero",
        "-D",
        help=tr_multi(
            "Loka dosiero por enigo (anstataux pozicia argumento)",
            "Local file as input (instead of positional argument)",
            "Fichier local comme entree (au lieu de l'argument positionnel)",
        ),
    ),
) -> None:
    """Enhance or expand existing text using AI.

    Takes existing text (from argument, file, or stdin pipe) and improves it
    using the configured LLM provider.  Provide enhancement instructions as
    the second positional argument (e.g. "make more formal", "expand with
    examples", "simplify for beginners").

    Supports multiple formats:
    - txt: plain text enhancement
    - md: Markdown enhancement (preserves Markdown structure)
    - json: JSON content enhancement (preserves JSON structure)
    - enc: encik knowledge entry expansion (with UUID linking via tools)

    When a file path is provided as input and ``--formato`` is omitted, the
    format is inferred from the file extension.

    Use ``--ligilo`` or ``--dosiero`` to provide the LLM with external context
    (a web page or local file) to reference during enhancement.

    Examples::

        agento plibonigi "This text needs improvement" "make more formal"
        agento plibonigi draft.md "expand with examples" -K enhanced.md
        cat notes.txt | agento plibonigi "simplify"
        agento plibonigi entry.enc "add biographical details" -f enc
        agento plibonigi draft.md "add citations" -l "https://example.com/source"
    """
    resolved_instruction = instruction or instrukcio_opt or ""

    if formato is None:
        inferred = _infer_format_from_input(input, dosiero)
        formato = inferred or "txt"

    if formato not in _SUPPORTED_FORMATS:
        error(
            tr_multi(
                f"Nevalida formato: {formato}. Validaj: {', '.join(_SUPPORTED_FORMATS)}",
                f"Invalid format: {formato}. Valid: {', '.join(_SUPPORTED_FORMATS)}",
                f"Format invalide: {formato}. Valides: {', '.join(_SUPPORTED_FORMATS)}",
            ),
        )
        raise typer.Exit(1)

    input_text = _resolve_input_text(input, dosiero)
    if not input_text.strip():
        error(
            tr_multi(
                "Neniu eniga teksto.",
                "No input text.",
                "Aucun texte d'entree.",
            ),
        )
        raise typer.Exit(1)

    context_str = ""
    if ligilo:
        if _fetch_text is None:
            error(tr_multi(
                "--ligilo postulas A-core version kun http-modulo. "
                "Bonvolu reinstali: uv pip install -e A-core --no-deps",
                "--ligilo requires A-core version with http module. "
                "Reinstall from local source: uv pip install -e A-core --no-deps",
                "--ligilo necessite une version de A-core avec le module http. "
                "Reinstallez : uv pip install -e A-core --no-deps",
            ))
            raise typer.Exit(1)

        if _core_html_to_text is not None:
            _offer_trafilatura_if_missing()

        try:
            info(tr_multi(
                f"Legas URL: {ligilo}",
                f"Fetching URL: {ligilo}",
                f"Lecture de l'URL : {ligilo}",
            ))
            fetched = _fetch_text(ligilo)
            text_content = _html_to_text(fetched)
            context_str = _truncate_context(text_content, f"Content from URL: {ligilo}")
            context_preview = context_str[:120].replace("\n", " ")
            info(tr_multi(
                f"Kunteksto: {len(context_str)} signoj -- {context_preview}",
                f"Context: {len(context_str)} chars -- {context_preview}",
                f"Contexte : {len(context_str)} caracteres -- {context_preview}",
            ))
        except Exception as e:
            error(tr_multi(
                f"Ne eblas legi URL {ligilo}: {e}",
                f"Cannot fetch URL {ligilo}: {e}",
                f"Impossible de lire l'URL {ligilo} : {e}",
            ))
            raise typer.Exit(1) from e

    result = enhance_text(
        text=input_text,
        instruction=resolved_instruction,
        formato=formato,
        provider_ref=provizanto or "",
        context=context_str,
        verbose=verbose,
        interject=interjekti,
    )

    if not result:
        error(
            tr_multi(
                "Neniu enhavo generita.",
                "No content generated.",
                "Aucun contenu genere.",
            ),
        )
        raise typer.Exit(1)

    success(
        tr_multi(
            "Plibonigita teksto:",
            "Enhanced text:",
            "Texte ameliore :",
        ),
    )
    print(f"\n{result}\n")

    saved_path: Path | None = None
    if konservi:
        ext_map = {"txt": ".txt", "md": ".md", "json": ".json", "enc": ".enc"}
        suffix = ext_map.get(formato, "")
        if suffix and not konservi.suffix:
            konservi = konservi.with_suffix(suffix)
        try:
            saved_path = _save_to_file(konservi, result)
        except Exception as e:
            error(
                tr_multi(
                    f"Konservado malsukcesis: {e}",
                    f"Saving failed: {e}",
                    f"Enregistrement echoue : {e}",
                ),
            )
            raise typer.Exit(1) from e

    if kopii:
        copy_target = str(saved_path) if saved_path else result
        ok, reason = copy_to_clipboard(copy_target)
        if not ok:
            warning(tr_multi(
                "Ne povis kopii al poŝo: {kialo}",
                "Could not copy to clipboard: {kialo}",
                "Impossible de copier dans le presse-papier : {kialo}",
            ).format(kialo=reason))
        else:
            info(
                tr_multi(
                    "Kopiita al tondujo.",
                    "Copied to clipboard.",
                    "Copie dans le presse-papiers.",
                ),
            )


__all__ = [
    "enhance_text",
    "plibonigi",
]
