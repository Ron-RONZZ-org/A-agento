from __future__ import annotations

from pathlib import Path

import typer

from A import tr_multi, info, success, warning

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
        import sys

        if typer.confirm(
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

                installers = [
                    ("uv pip", ["uv", "pip", "install", "trafilatura"]),
                    ("pip", ["pip", "install", "trafilatura"]),
                    ("python3 -m pip", ["python3", "-m", "pip", "install", "trafilatura"]),
                    (f"{sys.executable} -m pip", [sys.executable, "-m", "pip", "install", "trafilatura"]),
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
                pass
