"""Helper functions for the plibonigi command."""

from __future__ import annotations

import sys as _sys
from pathlib import Path

import typer

from A import tr_multi, error
from A_agento.commands._helpers import get_provider_or_exit
from A_agento.commands._knowledge_helpers import _clean_enc_output
from A_agento.commands._context_helpers import _read_local_file
from A_agento.prompt_loader import load_prompt

_SUPPORTED_FORMATS = ("txt", "md", "json", "enc")
_EXT_TO_FORMAT: dict[str, str] = {
    ".txt": "txt", ".md": "md", ".json": "json", ".enc": "enc",
}


def _build_enc_context_block(topic: str, max_entries: int = 20) -> str:
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
        return input_arg

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
    prompt = load_prompt(f"plibonigi_{formato}")
    if prompt:
        return prompt
    return load_prompt("plibonigi")


def enhance_text(
    text: str,
    instruction: str = "",
    formato: str = "txt",
    provider_ref: str = "",
    context: str = "",
    verbose: bool = False,
    interject: bool = False,
) -> str:
    provider = get_provider_or_exit(provider_ref) if provider_ref else get_provider_or_exit()

    if formato == "enc":
        provider._max_tokens = 16384

    prompt = _load_prompt_for_format(formato)

    if formato == "enc":
        filled = prompt.format(
            original_text=text,
            instruction=instruction,
            context="",
            enc_rules=load_prompt("enc_rules"),
        )
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
