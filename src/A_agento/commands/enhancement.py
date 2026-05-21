"""A-agento enhancement command -- agento plibonigi.

Provides both a CLI command (plibonigi) and an importable function
(enhance_text) for use by other A-modules.

Exports:
    enhance_text(text, instruction, formato, provider_ref, context) -> str
    plibonigi()  -- Typer CLI command
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, copy_to_clipboard
from A_agento.commands._helpers import get_provider_or_exit
from A_agento.commands.knowledge import (
    _clean_enc_output,
    _html_to_text,
    _read_local_file,
    _save_to_file,
    _truncate_context,
)
from A_agento.prompt_loader import load_prompt

# Lazy imports: A-core modules may not exist on older installations.
_fetch_text = None  # type: ignore
try:
    from A.core.http import fetch_text as _fetch_text
except ImportError:
    pass

_core_html_to_text = None  # type: ignore
try:
    from A.core.web import html_to_text as _core_html_to_text
except ImportError:
    pass


# ── Helpers ─────────────────────────────────────────────────────────────


_SUPPORTED_FORMATS = ("txt", "md", "json", "enc")
_EXT_TO_FORMAT: dict[str, str] = {
    ".txt": "txt", ".md": "md", ".json": "json", ".enc": "enc",
}
_MAX_CONTEXT_CHARS = 50_000


def _offer_trafilatura_if_missing() -> None:
    """Prompt user to install trafilatura if not available (best-effort)."""
    try:
        import trafilatura  # noqa: F401
    except ImportError:
        if typer.confirm(
            tr_multi(
                "Cu instali trafilatura (A-core[web]) por pli bona "
                "enhavo-eltiro el retpaghoj?",
                "Install trafilatura (A-core[web]) for better "
                "web page content extraction?",
                "Installer trafilatura (A-core[web]) pour une meilleure "
                "extraction du contenu web ?",
            ),
            default=True,
        ):
            info(tr_multi(
                "Instalas trafilatura...",
                "Installing trafilatura...",
                "Installation de trafilatura...",
            ))
            try:
                import subprocess

                installers = [
                    ("uv pip", ["uv", "pip", "install", "trafilatura"]),
                    ("pip", ["pip", "install", "trafilatura"]),
                    ("python3 -m pip", ["python3", "-m", "pip", "install", "trafilatura"]),
                    (f"{_sys.executable} -m pip", [_sys.executable, "-m", "pip", "install", "trafilatura"]),
                ]
                for label, cmd in installers:
                    try:
                        subprocess.check_call(
                            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        success(tr_multi(
                            "trafilatura instalita. Rekomencu la ordon por uzi ghin.",
                            "trafilatura installed. Restart the command to use it.",
                            "trafilatura installe. Reexecutez la commande pour l'utiliser.",
                        ))
                        return
                    except (FileNotFoundError, subprocess.CalledProcessError):
                        continue

                warning(tr_multi(
                    "Ne eblis instali trafilatura per iu ajn metodo. "
                    "Provu permane: uv pip install trafilatura",
                    "Could not install trafilatura via any method. "
                    "Try manually: uv pip install trafilatura",
                    "Impossible d'installer trafilatura. "
                    "Essayez manuellement : uv pip install trafilatura",
                ))
            except Exception:
                pass  # Best-effort only


def _build_enc_context_block(topic: str, max_entries: int = 20) -> str:
    """Search encik for entries related to *topic* and format as a reference block.

    Returns a string like::

        - scienco (#aa1f345c): sistema studo de la mondo

    Empty string if A-encik is not installed or no results found.
    """
    try:
        from A_encik.service import get_service

        svc = get_service()
        entries = svc.search_like(topic, limit=max_entries)
        if not entries:
            return ""

        lines: list[str] = []
        for e in entries:
            uid = (e.get("uuid") or "")[:8]
            title = e.get("titolo") or ""
            preview = (e.get("difinio") or "")[:80].replace("\n", " ")
            if uid and title:
                lines.append(f"- {title} (#{uid}): {preview}" if preview else f"- {title} (#{uid})")
        return "\n".join(lines) if lines else ""
    except ImportError:
        return ""
    except Exception:
        return ""


def _resolve_input_text(
    input_arg: str,
    dosiero: Path | None,
) -> str:
    """Resolve input text from argument, file path, or stdin.

    Priority:
    1. ``--dosiero`` flag (highest)
    2. Positional argument that is an existing file path
    3. Positional argument used as literal text
    4. stdin pipe (if not a TTY)

    Args:
        input_arg: Positional argument value.
        dosiero: Explicit ``--dosiero`` path.

    Returns:
        Resolved input text.

    Raises:
        typer.Exit: If no input can be resolved.
    """
    if dosiero:
        try:
            return _read_local_file(dosiero)
        except Exception as e:
            error(
                tr_multi(
                    f"Ne eblas legi dosieron {dosiero}: {e}",
                    f"Cannot read file {dosiero}: {e}",
                    f"Impossible de lire le fichier {dosiero} : {e}",
                ),
            )
            raise typer.Exit(1) from e

    if input_arg:
        path = Path(input_arg)
        if path.is_file():
            try:
                return _read_local_file(path)
            except Exception as e:
                error(
                    tr_multi(
                        f"Ne eblas legi dosieron {input_arg}: {e}",
                        f"Cannot read file {input_arg}: {e}",
                        f"Impossible de lire le fichier {input_arg} : {e}",
                    ),
                )
                raise typer.Exit(1) from e
        return input_arg  # Use as literal text

    # Stdin fallback
    if not _sys.stdin.isatty():
        try:
            return _sys.stdin.read()
        except Exception as e:
            error(
                tr_multi(
                    f"Ne eblas legi de enigo: {e}",
                    f"Cannot read from stdin: {e}",
                    f"Impossible de lire depuis l'entree standard : {e}",
                ),
            )
            raise typer.Exit(1) from e

    error(
        tr_multi(
            "Neniu eniga teksto. Provizu tekston, dosieron, aux tubigu enigon.",
            "No input text. Provide text, a file path, or pipe input.",
            "Aucun texte d'entree. Fournissez du texte, un chemin de fichier, ou un pipe.",
        ),
    )
    raise typer.Exit(1)


def _infer_format_from_input(
    input_arg: str,
    dosiero: Path | None,
) -> str | None:
    """Infer output format from file extension of the input path.

    Checks ``--dosiero`` first, then the positional argument if it is an
    existing file.  Returns ``None`` if no file path is found or the
    extension is not recognised.
    """
    path: Path | None = None
    if dosiero:
        path = dosiero
    elif input_arg:
        candidate = Path(input_arg)
        if candidate.is_file():
            path = candidate
    if path is None:
        return None
    return _EXT_TO_FORMAT.get(path.suffix.lower())


def _load_prompt_for_format(formato: str) -> str:
    """Load the appropriate prompt template for the given format.

    Tries ``plibonigi_{formato}.md`` first, falls back to ``plibonigi.md``.
    """
    prompt = load_prompt(f"plibonigi_{formato}")
    if prompt:
        return prompt
    return load_prompt("plibonigi")


# ── Exportable function (for other modules) ────────────────────────────


def enhance_text(
    text: str,
    instruction: str = "",
    formato: str = "txt",
    provider_ref: str = "",
    context: str = "",
    verbose: bool = False,
    interject: bool = False,
) -> str:
    """Enhance/expand *text* using the configured LLM provider.

    Args:
        text: Original text to enhance.
        instruction: How to enhance (e.g. "make more formal", "expand with examples").
        formato: Output format (txt/md/json/enc).
        provider_ref: Provider reference (uses prioritato fallback if empty).
        context: External context (web page content, URL content, etc.).
        verbose: Show the full LLM conversation.
        interject: Allow user interjection during generation.

    Returns:
        Enhanced text.

    Raises:
        typer.Exit: If provider cannot be resolved or generation fails.
    """
    provider = get_provider_or_exit(provider_ref) if provider_ref else get_provider_or_exit()

    if formato == "enc":
        # Increase token limit for .enc expansion (tool calls + existing content)
        provider._max_tokens = 16384

    prompt = _load_prompt_for_format(formato)

    if formato == "enc":
        # Tool-based expansion: build messages with warm context
        filled = prompt.format(
            original_text=text,
            instruction=instruction,
            context="",
            enc_rules=load_prompt("enc_rules"),
        )
        # Warm context: pre-populate with existing entries related to the content
        search_topic = instruction[:80] if instruction else text[:80]
        context_block = _build_enc_context_block(search_topic)
        if context_block:
            filled += f"\n\n# Existing entries you can reference directly\n{context_block}"

        from A_agento.tools import ENCIK_TOOLS, generate_with_tools

        messages = [{"role": "user", "content": filled}]
        if context:
            messages.append({
                "role": "user",
                "content": context,
                "_display_hint": "external_context",
            })

        try:
            content = generate_with_tools(
                provider, messages, tools=ENCIK_TOOLS,
                verbose=verbose, interject=interject,
            )
        except Exception as e:
            error(
                tr_multi(
                    f"Plibonigo malsukcesis: {e}",
                    f"Enhancement failed: {e}",
                    f"Amelioration echouee : {e}",
                ),
            )
            raise typer.Exit(1) from e

        content = _clean_enc_output(content)
    else:
        # Simple format-preserving enhancement
        filled = prompt.format(
            formato=formato,
            original_text=text,
            instruction=instruction,
            context=context,
        )
        try:
            content = provider.generate(filled)
        except Exception as e:
            error(
                tr_multi(
                    f"Plibonigo malsukcesis: {e}",
                    f"Enhancement failed: {e}",
                    f"Amelioration echouee : {e}",
                ),
            )
            raise typer.Exit(1) from e

    return content.strip()


# ── CLI command ────────────────────────────────────────────────────────


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
        "--verbose",
        "--detala",
        "-v",
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
    # ── Resolve instruction ─────────────────────────────────────────────
    # Prefer positional ($2); fall back to --instrukcio (long-form only,
    # no short flag), which is useful when piping stdin.
    resolved_instruction = instruction or instrukcio_opt or ""

    # ── Resolve format ──────────────────────────────────────────────────
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

    # ── Resolve input text ──────────────────────────────────────────────
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

    # ── Build external context from --ligilo ────────────────────────────
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

    # ── Enhance ─────────────────────────────────────────────────────────
    provider = get_provider_or_exit(provizanto)

    info(
        tr_multi(
            f"Plibonigas enhavon ({formato})...",
            f"Enhancing content ({formato})...",
            f"Ameiloration du contenu ({formato})...",
        ),
    )

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

    # ── Output ──────────────────────────────────────────────────────────
    success(
        tr_multi(
            "Plibonigita teksto:",
            "Enhanced text:",
            "Texte ameliore :",
        ),
    )
    print(f"\n{result}\n")

    # ── --konservi (save to file) ───────────────────────────────────────
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

    # ── --kopii (copy to clipboard) ─────────────────────────────────────
    if kopii:
        copy_target = str(saved_path) if saved_path else result
        copy_to_clipboard(copy_target)
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
