"""Prompt loader with file-based override support.

Three-tier loading:
1. ~/.config/A/agento/prompts/<name>.md — user override
2. src/A_agento/prompts/<name>.md — packaged default
3. Embedded string in code — last resort fallback

Users can copy .md files to ~/.config/A/agento/prompts/ and edit.
Prompt engineers edit the .md files in the repo (no Python code).
"""

from __future__ import annotations

from pathlib import Path

from A.core.paths import config_dir

# Directory where user's custom prompt files live
_USER_PROMPT_DIR: Path = config_dir() / "agento" / "prompts"
# Directory where packaged default prompt files live
_PKG_PROMPT_DIR: Path = Path(__file__).parent / "prompts"
# In-memory cache: name -> content
_CACHE: dict[str, str] = {}


def load_prompt(name: str, default: str = "") -> str:
    """Load a prompt by name, with three-tier fallback.

    Priority:
    1. ~/.config/A/agento/prompts/<name>.md — user override
    2. src/A_agento/prompts/<name>.md — packaged default
    3. Embedded `default` string — last resort

    Results are cached in memory after first load.

    Args:
        name: Prompt identifier (e.g. "generi_enc", "system_base")
        default: Embedded fallback string (used if no file found)

    Returns:
        Prompt string
    """
    if name in _CACHE:
        return _CACHE[name]

    # 1. User override
    path = _USER_PROMPT_DIR / f"{name}.md"
    if path.exists():
        content = path.read_text(encoding="utf-8")
        _CACHE[name] = content
        return content

    # 2. Packaged default
    pkg_path = _PKG_PROMPT_DIR / f"{name}.md"
    if pkg_path.exists():
        content = pkg_path.read_text(encoding="utf-8")
        _CACHE[name] = content
        return content

    # 3. Embedded fallback
    _CACHE[name] = default
    return default


def clear_cache() -> None:
    """Clear the prompt cache (useful for testing)."""
    _CACHE.clear()


def get_prompt_dir() -> Path:
    """Get the user prompt directory path."""
    return _USER_PROMPT_DIR


__all__ = [
    "load_prompt",
    "clear_cache",
    "get_prompt_dir",
]
