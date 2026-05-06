"""Prompt loader with file-based override support.

Loads prompts from ~/.config/A/agento/prompts/<name>.prompt if available.
Falls back to embedded defaults in code. Caches loaded prompts in memory.

Users can copy .prompt.example files to .prompt and edit them to customize
AI behavior without modifying Python code.
"""

from __future__ import annotations

from pathlib import Path

from A.core.paths import config_dir

# Directory where user's custom prompt files live
_PROMPT_DIR: Path = config_dir() / "agento" / "prompts"
# In-memory cache: name → content
_CACHE: dict[str, str] = {}


def load_prompt(name: str, default: str) -> str:
    """Load a prompt by name, with file-based override support.

    Checks ~/.config/A/agento/prompts/<name>.prompt first.
    If the file doesn't exist, returns the embedded default.

    Results are cached in memory after first load.

    Args:
        name: Prompt identifier (e.g. "system_base", "summarize_template")
        default: Embedded default prompt string

    Returns:
        Prompt string (from file or default)
    """
    if name in _CACHE:
        return _CACHE[name]

    path = _PROMPT_DIR / f"{name}.prompt"
    if path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = default

    _CACHE[name] = content
    return content


def clear_cache() -> None:
    """Clear the prompt cache (useful for testing)."""
    _CACHE.clear()


def get_prompt_dir() -> Path:
    """Get the prompt directory path."""
    return _PROMPT_DIR


__all__ = [
    "load_prompt",
    "clear_cache",
    "get_prompt_dir",
]
