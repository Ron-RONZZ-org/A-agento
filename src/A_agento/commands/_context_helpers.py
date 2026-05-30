from __future__ import annotations

from pathlib import Path

import typer

from A import tr_multi, success, warning

_core_html_to_text = None
try:
    from A.core.web import html_to_text as _core_html_to_text
except ImportError:
    pass

_MAX_FILE_BYTES = 5_000_000
_MAX_CONTEXT_CHARS = 50_000


def _html_to_text(html: str) -> str:
    if _core_html_to_text is not None:
        return _core_html_to_text(html)
    import re
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate_context(text: str, source_label: str) -> str:
    if len(text) <= _MAX_CONTEXT_CHARS:
        return f"## {source_label}\n\n{text}"
    return (
        f"## {source_label}\n\n{text[:_MAX_CONTEXT_CHARS]}"
        f"\n\n[... context truncated to {_MAX_CONTEXT_CHARS} characters ...]"
    )


def _read_local_file(path: Path) -> str:
    real = path.expanduser().resolve()

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

    try:
        return real.read_text("utf-8")
    except UnicodeDecodeError:
        return real.read_text("latin-1")


def _offer_trafilatura_if_missing() -> None:
    try:
        import trafilatura  # noqa: F401
    except ImportError:
        from A.utils.deps import ensure_dependency

        try:
            ensure_dependency("trafilatura")
            success(tr_multi(
                "trafilatura instalita. Rekomencu la ordon por uzi ghin.",
                "trafilatura installed. Restart the command to use it.",
                "trafilatura installé. Réexécutez la commande pour l'utiliser.",
            ))
        except ImportError:
            warning(tr_multi(
                "Ne eblis instali trafilatura. "
                "Provu permane: uv pip install trafilatura",
                "Could not install trafilatura. "
                "Try manually: uv pip install trafilatura",
                "Impossible d'installer trafilatura. "
                "Essayez manuellement : uv pip install trafilatura",
            ))
