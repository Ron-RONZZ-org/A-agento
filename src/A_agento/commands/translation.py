"""A-agento translation command — agento traduki.

Provides both a CLI command (traduki) and an importable function
(translate_text) for use by other A-modules.

Exports:
    translate_text(text, target, source, provider_ref) -> str
    traduki()  — Typer CLI command
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from A import tr, tr_multi, info, error, success, copy_to_clipboard
from A_agento.commands._helpers import get_provider_or_exit
from A_agento.commands.knowledge import _read_local_file, _save_to_file
from A_agento.prompt_loader import load_prompt


# ── Exportable function (for other modules) ────────────────────────────────


def translate_text(
    text: str,
    target: str = "",
    source: str = "",
    provider_ref: str = "",
) -> str:
    """Translate *text* using the configured LLM provider.

    Args:
        text: Text to translate.
        target: Target language code (e.g. ``'en'``, ``'fr'``).
            Auto-detected if empty.
        source: Source language code. Auto-detected if empty.
        provider_ref: Provider reference (uses prioritato fallback if empty).

    Returns:
        Translated text.

    Raises:
        typer.Exit: If provider cannot be resolved or generation fails.
    """
    provider = get_provider_or_exit(provider_ref) if provider_ref else get_provider_or_exit()

    to_target = f" to {target}" if target else ""
    from_source = f" from {source}" if source else ""

    prompt = load_prompt("traduki").format(
        to_target=to_target,
        from_source=from_source,
        text=text,
    )

    try:
        return provider.generate(prompt).strip()
    except Exception as e:
        error(
            tr_multi(
                f"Traduko malsukcesis: {e}",
                f"Translation failed: {e}",
                f"Traduction échouée : {e}",
            ),
        )
        raise typer.Exit(1) from e


# ── CLI command ────────────────────────────────────────────────────────────


def traduki(
    input: str = typer.Argument(
        ...,
        help=tr_multi(
            "Teksto aŭ dosiero por traduki",
            "Text or file to translate",
            "Texte ou fichier à traduire",
        ),
    ),
    celo: Optional[str] = typer.Option(
        None,
        "--celo",
        "-c",
        help=tr_multi(
            "Cela lingvo (ekz: 'en', 'fr'). Aŭtomate detektita se ne specifita.",
            "Target language (e.g. 'en', 'fr'). Auto-detected if not specified.",
            "Langue cible (ex: 'en', 'fr'). Auto-détectée si non spécifiée.",
        ),
    ),
    fonto: Optional[str] = typer.Option(
        None,
        "--fonto",
        "-f",
        help=tr_multi(
            "Fontlingvo (ekz: 'en', 'fr'). Aŭtomate detektita se ne specifita.",
            "Source language (e.g. 'en', 'fr'). Auto-detected if not specified.",
            "Langue source (ex: 'en', 'fr'). Auto-détectée si non spécifiée.",
        ),
    ),
    konservi: Optional[Path] = typer.Option(
        None,
        "--konservi",
        "-K",
        help=tr_multi(
            "Dosiero por konservi la tradukon",
            "File to save the translation to",
            "Fichier pour sauvegarder la traduction",
        ),
    ),
    kopii: bool = typer.Option(
        False,
        "--kopii",
        "-k",
        help=tr_multi(
            "Kopii la rezulton al tondujo",
            "Copy the result to clipboard",
            "Copier le résultat dans le presse-papiers",
        ),
    ),
    provizanto: Optional[str] = typer.Option(
        None,
        "--provizanto",
        "-p",
        help=tr_multi(
            "Provizanto, provizanto:profilon, aŭ UUID. Vidu 'agento agordi ls' por listo.",
            "Provider name, provider:profile, or config UUID. See 'agento agordi ls' for available.",
            "Nom du fournisseur, fournisseur:profil, ou UUID de config. Voir 'agento agordi ls' pour la liste.",
        ),
    ),
    dosiero: Optional[Path] = typer.Option(
        None,
        "--dosiero",
        "-D",
        help=tr_multi(
            "Legi enigon el dosiero (aŭtomate detektita se la argumento estas dosiervojo)",
            "Read input from file (auto-detected if argument is a file path)",
            "Lire l'entrée depuis un fichier (auto-détecté si l'argument est un chemin)",
        ),
    ),
) -> None:
    """Translate text using AI.

    Translates text from one language to another using the configured LLM
    provider.  Input can be provided as a string argument, a file path
    (auto-detected), or explicitly via ``--dosiero``.

    If ``--celo`` is omitted the source language is auto-detected and the
    target language defaults to the configured value (typically English).

    Examples::

        agento traduki "Hello world" -c fr
        agento traduki doc.txt -c eo -K tradukita.md
        agento traduki "Bonjour" -c en -k
    """
    # ── Resolve input text ──────────────────────────────────────────────
    input_text: str = ""

    if not input or not input.strip():
        error(
            tr_multi(
                "Neniu eniga teksto.",
                "No input text.",
                "Aucun texte d'entrée.",
            ),
        )
        raise typer.Exit(1)

    if dosiero:
        try:
            input_text = _read_local_file(dosiero)
        except Exception as e:
            error(
                tr_multi(
                    f"Ne eblas legi dosieron {dosiero}: {e}",
                    f"Cannot read file {dosiero}: {e}",
                    f"Impossible de lire le fichier {dosiero} : {e}",
                ),
            )
            raise typer.Exit(1) from e
    else:
        path = Path(input)
        if path.is_file():
            try:
                input_text = _read_local_file(path)
            except Exception as e:
                error(
                    tr_multi(
                        f"Ne eblas legi dosieron {input}: {e}",
                        f"Cannot read file {input}: {e}",
                        f"Impossible de lire le fichier {input} : {e}",
                    ),
                )
                raise typer.Exit(1) from e
        else:
            input_text = input

    # ── Translate ───────────────────────────────────────────────────────
    provider = get_provider_or_exit(provizanto)
    to_target = f" to {celo}" if celo else ""
    from_source = f" from {fonto}" if fonto else ""

    prompt = load_prompt("traduki").format(
        to_target=to_target,
        from_source=from_source,
        text=input_text,
    )

    info(
        tr_multi(
            "Tradukas...",
            "Translating...",
            "Traduction...",
        ),
    )

    try:
        result = provider.generate(prompt).strip()
    except Exception as e:
        error(
            tr_multi(
                f"Traduko malsukcesis: {e}",
                f"Translation failed: {e}",
                f"Traduction échouée : {e}",
            ),
        )
        raise typer.Exit(1) from e

    if not result:
        error(
            tr_multi(
                "Neniu traduko ricevita.",
                "No translation received.",
                "Aucune traduction reçue.",
            ),
        )
        raise typer.Exit(1)

    # ── Output ──────────────────────────────────────────────────────────
    success(
        tr_multi(
            "Traduko:",
            "Translation:",
            "Traduction :",
        ),
    )
    print(f"\n{result}\n")

    # ── --konservi (save to file) ───────────────────────────────────────
    saved_path: Path | None = None
    if konservi:
        try:
            saved_path = _save_to_file(konservi, result)
        except Exception as e:
            error(
                tr_multi(
                    f"Konservado malsukcesis: {e}",
                    f"Saving failed: {e}",
                    f"Enregistrement échoué : {e}",
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
                "Copié dans le presse-papiers.",
            ),
        )


__all__ = [
    "translate_text",
    "traduki",
]