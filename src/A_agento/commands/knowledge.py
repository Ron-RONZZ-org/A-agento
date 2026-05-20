from __future__ import annotations

"""A-agento AI commands for text generation.

Functions:
- generi: Generate content with AI (txt, md, json, enc formats)
"""

import json
from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, warning, copy_to_clipboard
from A_agento.commands._helpers import get_provider_or_exit

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

from A_agento.tools import generate_with_tools, ENCIK_TOOLS
from A_agento.prompt_loader import load_prompt


# ── Format-specific prompt builders ──────────────────────────────────────────


def _get_format_prompt(formato: str) -> str:
    """Load a format prompt with three-tier fallback.

    1. ~/.config/A/agento/prompts/generi_<formato>.md (user override)
    2. src/A_agento/prompts/generi_<formato>.md (packaged default)
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

    - Removes any text before the first code fence (```), then strips
      the fence itself
    - Removes any text after the last code fence, then strips the fence
    - Handles ```, ```enc, ```toml, etc.
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

    # Strip code fences anywhere in the content.
    # Extract the LAST code block only (LLM may generate multiple drafts
    # before arriving at a final version — earlier drafts are discarded).
    fence_pattern = r'```\w*'
    fences = list(re.finditer(fence_pattern, content))
    if len(fences) >= 2:
        # Take the last pair of fences (last code block)
        first = fences[-2].start()
        last = fences[-1].end()
        # Extract content between second-to-last fence's end and last fence's start
        after_first = content[first:].split('\n', 1)
        before_last = content[:last].rsplit('\n', 1)
        if len(after_first) > 1 and len(before_last) > 1:
            start_content = first + len(after_first[0]) + 1  # skip first fence line
            end_content = last - len(before_last[-1]) - 1     # before last fence line
            if start_content < end_content:
                content = content[start_content:end_content]
            else:
                content = content[end_content:start_content] if end_content < start_content else ""
    elif len(fences) == 1:
        # Single fence: determine if opening (has lang tag like ```enc) or closing (just ```)
        f = fences[0]
        fence_text = f.group(0)
        is_opening = len(fence_text) > 3  # ```enc > ``` (more than just backticks)
        after_fence = content[f.end():]   # everything after the fence line
        if is_opening:
            # Opening fence with lang tag: remove everything up to fence, keep rest
            content = after_fence.lstrip('\n')
        else:
            # Closing fence with no lang tag: remove from fence to end
            content = content[:f.start()].rstrip('\n')

    # Strip leading # title comments (tolerated by parser but not desired style)
    lines = content.split('\n')
    while lines and lines[0].startswith('#') and not lines[0].startswith('##'):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)

    return '\n'.join(lines).strip()


def _resolve_unique_path(path: Path) -> Path:
    """Return *path* if it doesn't exist, or a numbered variant.

    Appends ``.1``, ``.2``, etc. before the extension to avoid
    overwriting existing files.  Never prompts interactively.

    Examples::

        a.enc            → a.enc       (no conflict)
        a.enc            → a.1.enc     (conflict)
        a.1.enc          → a.1.1.enc   (conflict)
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for n in range(1, 1000):
        candidate = parent / f"{stem}.{n}{suffix}"
        if not candidate.exists():
            return candidate
    # 999 files — extremely unlikely. Fall back to timestamp.
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"{stem}.{ts}{suffix}"


def _save_to_file(path: Path, content: str, titolo: str = "") -> Path | None:
    """Save generated content to a file, auto-resolving conflicts.

    If the file already exists, a numbered suffix is appended
    automatically (never prompts interactively — avoids Rich Console
    stdout conflicts with stdin-based prompts).

    Args:
        path: Output file path
        content: Content to write
        titolo: Optional title for user feedback

    Returns:
        The final path the file was saved to, or None on error.
    """
    import sys as _sys

    final_path = _resolve_unique_path(path)
    final_path.parent.mkdir(parents=True, exist_ok=True)

    if final_path != path:
        info(tr_multi(
            f"{path} jam ekzistas. Konservas kiel {final_path}",
            f"{path} already exists. Saving as {final_path}",
            f"{path} existe déjà. Enregistre comme {final_path}",
        ))

    try:
        with open(str(final_path), "w", encoding="utf-8") as _f:
            _f.write(content)
    except Exception as e:
        _sys.stderr.write(f"[SAVE_ERROR] {type(e).__name__}: {e}\n")
        _sys.stderr.flush()
        raise

    success(
        tr_multi(
            f"Konservita al {final_path}",
            f"Saved to {final_path}",
            f"Enregistré dans {final_path}",
        )
    )
    return final_path


def _build_context_block(topic: str, max_entries: int = 20) -> str:
    """Search encik for entries related to *topic* and format as a reference block.

    Returns a string like::

        - scienco (#aa1f345c): sistema studo de la mondo
        - libro (#827b73b8): kolekto de skribitaj paghoj

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


_MAX_FILE_BYTES = 5_000_000
_MAX_CONTEXT_CHARS = 50_000


def _html_to_text(html: str) -> str:
    """Strip HTML tags and return plain text.

    Delegates to ``A.core.web.html_to_text()`` for trafilatura-backed
    extraction with LaTeX noise removal.  Falls back to raw tag stripping
    if A-core version is too old.
    """
    if _core_html_to_text is not None:
        return _core_html_to_text(html)
    # Fallback: basic tag stripping via regex
    import re
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate_context(text: str, source_label: str) -> str:
    """Truncate *text* to ``_MAX_CONTEXT_CHARS``, appending a notice if cut."""
    if len(text) <= _MAX_CONTEXT_CHARS:
        return f"## {source_label}\n\n{text}"
    return (
        f"## {source_label}\n\n{text[:_MAX_CONTEXT_CHARS]}"
        f"\n\n[... context truncated to {_MAX_CONTEXT_CHARS} characters ...]"
    )


def _read_local_file(path: Path) -> str:
    """Read a local file with path traversal protection and size limit.

    Args:
        path: Path to the file to read.

    Returns:
        File contents as decoded text.

    Raises:
        ValueError: If file exceeds size limit or cannot be read.
    """
    real = path.expanduser().resolve()

    # Warn on potentially sensitive paths
    sensitive_parents: list[Path] = [
        Path.home() / ".ssh",
        Path("/etc"),
        Path("/proc"),
        Path("/sys"),
    ]
    for sp in sensitive_parents:
        try:
            if sp in real.parents or real == sp:
                warning(tr_multi(
                    f"Atentu: legas eble sentivan dosieron {path}",
                    f"Warning: reading potentially sensitive file {path}",
                    f"Attention : lecture d'un fichier potentiellement sensible {path}",
                ))
                break
        except (OSError, ValueError):
            continue

    # Size check before reading
    try:
        sz = real.stat().st_size
    except OSError as e:
        raise ValueError(f"Cannot stat file: {e}")
    if sz > _MAX_FILE_BYTES:
        raise ValueError(
            tr_multi(
                f"Dosiero tro granda ({sz} bajtoj). Maksimumo: {_MAX_FILE_BYTES} bajtoj.",
                f"File too large ({sz} bytes). Maximum: {_MAX_FILE_BYTES} bytes.",
                f"Fichier trop volumineux ({sz} octets). Maximum : {_MAX_FILE_BYTES} octets.",
            )
        )

    # Read with encoding fallback
    try:
        return real.read_text("utf-8")
    except UnicodeDecodeError:
        return real.read_text("latin-1")


def _offer_trafilatura_if_missing() -> None:
    """Prompt user to install trafilatura if not available (best-effort)."""
    try:
        import trafilatura  # noqa: F401
    except ImportError:
        import sys as _sys
        import typer as _typer

        if _typer.confirm(
            tr_multi(
                "Ĉu instali trafilatura (A-core[web]) por pli bona "
                "enhavo-eltiro el retpaĝoj?",
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
                import sys as _sys

                # Venv-aware fallback chain (from AGENTS.md policy)
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
                            "trafilatura installé. Réexécutez la commande pour l'utiliser.",
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
        "-K",
        help=tr_multi(
            "Dosiero por konservi la rezulton (ekz: eligo.enc)",  # eo
            "File path to save the result (e.g. output.enc)",  # en
            "Chemin du fichier pour sauvegarder le resultat (ex: sortie.enc)",  # fr
        ),
    ),
    kopii: bool = typer.Option(
        False,
        "--kopii",
        "-k",
        help=tr_multi(
            "Kopii la vojon de la konservita dosiero al tondujo (bezonas --konservi)",  # eo
            "Copy the saved file path to clipboard (requires --konservi)",  # en
            "Copier le chemin du fichier sauvegardé dans le presse-papiers (nécessite --konservi)",  # fr
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
    ligilo: Optional[str] = typer.Option(
        None,
        "--ligilo",
        "-l",
        help=tr_multi(
            "URL de retpagho por kunteksto (LLM legos ghin)",  # eo
            "Web page URL to attach as context (LLM will read it)",  # en
            "URL de page Web à attacher comme contexte (le LLM la lira)",  # fr
        ),
    ),
    dosiero: Optional[Path] = typer.Option(
        None,
        "--dosiero",
        "-D",
        help=tr_multi(
            "Loka dosiero por kunteksto (LLM legos ghin)",  # eo
            "Local file to attach as context (LLM will read it)",  # en
            "Fichier local à attacher comme contexte (le LLM le lira)",  # fr
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
                f"Nevalida formato: {formato}. Validaj: {', '.join(valid_formats)}",  # eo
                f"Invalid format: {formato}. Valid: {', '.join(valid_formats)}",  # en
                f"Format invalide: {formato}. Valides: {', '.join(valid_formats)}",  # fr
            )
        )
        raise typer.Exit(1)

    provider = get_provider_or_exit(provizanto)
    # Increase token limit for .enc generation (full entries with tool calls)
    if formato == "enc":
        provider._max_tokens = 16384
    title_line = f"Title: {titolo}" if titolo else ""

    # ── Build context from --ligilo / --dosiero ──────────────────────────
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

        # Offer trafilatura for better extraction (optional)
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
        f"Generas enhavon ({formato})...",  # eo
        f"Generating content ({formato})...",  # en
        f"Génération du contenu ({formato})...",  # fr
    ))

    try:
        prompt_text = _get_format_prompt(formato)
        if formato == "enc":
            prompt = prompt_text.format(
                title_line=title_line, prompto=prompto, context=context_str,
            )
            # Warm context: pre-populate with existing entries relevant to the topic
            context_block = _build_context_block(prompto)
            if context_block:
                prompt += f"\n\n# Existing entries you can reference directly\n{context_block}"
            messages = [{"role": "user", "content": prompt}]
            content = generate_with_tools(provider, messages, tools=ENCIK_TOOLS, verbose=verbose, interject=interjekti)
            content = _clean_enc_output(content)
        else:
            prompt = prompt_text.format(title_line=title_line, prompto=prompto, context=context_str)
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
        # Auto-append file extension if missing
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
