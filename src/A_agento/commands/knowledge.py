from __future__ import annotations

"""A-agento AI commands for text generation.

Functions:
- generi: Generate content with AI (txt, md, json, enc formats)
"""

from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, copy_to_clipboard
from A_agento.commands._helpers import get_provider_or_exit
from A_agento.commands._context_helpers import (
    _core_html_to_text,
    _html_to_text,
    _truncate_context,
    _read_local_file,
    _offer_trafilatura_if_missing,
    _MAX_FILE_BYTES,
)
from A_agento.commands._knowledge_helpers import (
    _get_format_prompt,
    _clean_enc_output,
    _resolve_unique_path,
    _save_to_file,
    _build_context_block,
)
from A_agento.tools import generate_with_tools, ENCIK_TOOLS
from A_agento.prompt_loader import load_prompt

_fetch_text = None
try:
    from A.core.http import fetch_text as _fetch_text
except ImportError:
    pass


def generi(
    prompto: str = typer.Argument(
        ...,
        help=tr_multi(
            "Temo au priskribo por la enhavo",
            "Topic or description for the content",
            "Sujet ou description du contenu",
        ),
    ),
    formato: str = typer.Option(
        "txt",
        "--formato",
        "-f",
        help=tr_multi(
            "Formato (txt/md/json/enc)",
            "Format (txt/md/json/enc)",
            "Format (txt/md/json/enc)",
        ),
    ),
    titolo: Optional[str] = typer.Option(
        None,
        "--titolo",
        "-t",
        help=tr_multi(
            "Titolo (au autogenerita se ne donita)",
            "Title (auto-generated if omitted)",
            "Titre (auto-genere si omis)",
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "Provizanto, provizanto:profilon, aux UUID. Vidu 'agento agordi ls' por listo.",
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",
        ),
    ),
    konservi: Optional[Path] = typer.Option(
        None,
        "--konservi",
        "-K",
        help=tr_multi(
            "Dosiero por konservi la rezulton (ekz: eligo.enc)",
            "File path to save the result (e.g. output.enc)",
            "Chemin du fichier pour sauvegarder le resultat (ex: sortie.enc)",
        ),
    ),
    kopii: bool = typer.Option(
        False,
        "--kopii",
        "-k",
        help=tr_multi(
            "Kopii la vojon de la konservita dosiero al tondujo (bezonas --konservi)",
            "Copy the saved file path to clipboard (requires --konservi)",
            "Copier le chemin du fichier sauvegardé dans le presse-papiers (nécessite --konservi)",
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "--detala",
        "-v",
        help=tr_multi(
            "Montri la plenan konversacion kun LLM (inkluzive de pensado)",
            "Show full LLM conversation (including reasoning/thinking)",
            "Afficher la conversation complète avec LLM (y compris le raisonnement)",
        ),
    ),
    interjekti: bool = typer.Option(
        False,
        "--interjekti",
        "--interject",
        "-i",
        help=tr_multi(
            "Premu 'x' iam ajn por paŭzi kaj korekti. Uzu kun --detala.",
            "Press 'x' at any time to pause and type a correction. Use with --detala.",
            "Appuyez sur 'x' à tout moment pour corriger. À utiliser avec --detala.",
        ),
    ),
    ligilo: Optional[str] = typer.Option(
        None,
        "--ligilo",
        "-l",
        help=tr_multi(
            "URL de retpagho por kunteksto (LLM legos ghin)",
            "Web page URL to attach as context (LLM will read it)",
            "URL de page Web à attacher comme contexte (le LLM la lira)",
        ),
    ),
    dosiero: Optional[Path] = typer.Option(
        None,
        "--dosiero",
        "-D",
        help=tr_multi(
            "Loka dosiero por kunteksto (LLM legos ghin)",
            "Local file to attach as context (LLM will read it)",
            "Fichier local à attacher comme contexte (le LLM le lira)",
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

    Use --ligilo or --dosiero to provide the LLM with external context
    (a web page or local file) to base the generation on.

    If --konservi is given, saves to file for manual review.
    For .enc format, the AI can search your encik database for related
    entries to create proper links with real UUIDs.

    Examples:
        agento generi "Explain quantum computing"
        agento generi "macOS" --formato enc
        agento generi "Notes" --formato md --konservi notes.md
        agento generi "Summarise this" --ligilo "https://example.com/article"
        agento generi "Translate this" --dosiero ~/doc.txt
        agento generi "Compare sources" --ligilo "https://a.com" --dosiero ~/notes.md
        agento generi "Python" --formato enc --konservi eligo.enc
    """
    valid_formats = ("txt", "md", "json", "enc")
    if formato not in valid_formats:
        error(
            tr_multi(
                f"Nevalida formato: {formato}. Validaj: {', '.join(valid_formats)}",
                f"Invalid format: {formato}. Valid: {', '.join(valid_formats)}",
                f"Format invalide: {formato}. Valides: {', '.join(valid_formats)}",
            )
        )
        raise typer.Exit(1)

    provider = get_provider_or_exit(provizanto)
    if formato == "enc":
        provider._max_tokens = 16384
    title_line = f"Title: {titolo}" if titolo else ""

    context_parts: list[str] = []
    if ligilo:
        if _fetch_text is None:
            error(tr_multi(
                "--ligilo postulas A-core version kun http-modulo. "
                "Bonvolu reinstali: uv pip install -e A-core --no-deps",
                "--ligilo requires A-core version with http module. "
                "Reinstall from local source: uv pip install -e A-core --no-deps",
                "--ligilo nécessite une version de A-core avec le module http. "
                "Réinstallez : uv pip install -e A-core --no-deps",
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
            context_parts.append(
                _truncate_context(text_content, f"Content from URL: {ligilo}")
            )
        except Exception as e:
            error(tr_multi(
                f"Ne eblas legi URL {ligilo}: {e}",
                f"Cannot fetch URL {ligilo}: {e}",
                f"Impossible de lire l'URL {ligilo} : {e}",
            ))
            raise typer.Exit(1) from e

    if dosiero:
        try:
            dosiero_content = _read_local_file(dosiero)
            context_parts.append(
                _truncate_context(dosiero_content, f"Content from file: {dosiero}")
            )
        except Exception as e:
            error(tr_multi(
                f"Ne eblas legi dosieron {dosiero}: {e}",
                f"Cannot read file {dosiero}: {e}",
                f"Impossible de lire le fichier {dosiero} : {e}",
            ))
            raise typer.Exit(1)

    context_str = "\n\n".join(context_parts)

    info(tr_multi(
        f"Generas enhavon ({formato})...",
        f"Generating content ({formato})...",
        f"Génération du contenu ({formato})...",
    ))

    try:
        prompt_text = _get_format_prompt(formato)
        if formato == "enc":
            prompt = prompt_text.format(
                title_line=title_line, prompto=prompto, context="",
                enc_rules=load_prompt("enc_rules"),
            )
            context_block = _build_context_block(prompto)
            if context_block:
                prompt += f"\n\n# Existing entries you can reference directly\n{context_block}"
            messages = [{"role": "user", "content": prompt}]
            if context_str:
                messages.append({
                    "role": "user",
                    "content": context_str,
                    "_display_hint": "external_context",
                })
                context_preview = context_str[:120].replace("\n", " ")
                info(tr_multi(
                    f"📎 Kunteksto: {len(context_str)} signoj — {context_preview}",
                    f"📎 Context: {len(context_str)} chars — {context_preview}",
                    f"📎 Contexte : {len(context_str)} caractères — {context_preview}",
                ))
            content = generate_with_tools(provider, messages, tools=ENCIK_TOOLS, verbose=verbose, interject=interjekti)
            content = _clean_enc_output(content)
        else:
            prompt = prompt_text.format(title_line=title_line, prompto=prompto, context=context_str)
            content = provider.generate(prompt)
    except Exception as e:
        error(
            tr_multi(
                f"Generado malsukcesis: {e}",
                f"Generation failed: {e}",
                f"Génération échouée: {e}",
            )
        )
        raise typer.Exit(1) from e

    if not content or not content.strip():
        error(
            tr_multi(
                "Neniu enhavo generita.",
                "No content generated.",
                "Aucun contenu généré.",
            )
        )
        raise typer.Exit(1)

    title_display = titolo or prompto[:40]
    print(f"\n[ {title_display} ]\n")
    print(content.strip())
    print()

    success(
        tr_multi(
            "Enhavo generita sukcese.",
            "Content generated successfully.",
            "Contenu généré avec succès.",
        )
    )

    if konservi:
        ext_map = {"txt": ".txt", "md": ".md", "json": ".json", "enc": ".enc"}
        suffix = ext_map.get(formato, "")
        if suffix and not konservi.suffix:
            konservi = konservi.with_suffix(suffix)
        try:
            final_path = _save_to_file(konservi, content.strip(), titolo or prompto)
            if kopii and final_path is not None:
                copy_to_clipboard(str(final_path))
        except Exception as e:
            import sys as _sys
            _sys.stderr.write(f"[SAVE_ERROR] {type(e).__name__}: {e}\n")
            _sys.stderr.flush()
            error(
                tr_multi(
                    f"Konservado malsukcesis: {e}",
                    f"Saving failed: {e}",
                    f"Enregistrement échoué : {e}",
                )
            )
            raise typer.Exit(1) from e


__all__ = [
    "generi",
]
