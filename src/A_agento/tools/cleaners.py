"""Output validation and cleaning for LLM tool results."""

from __future__ import annotations

import json
import re


def _looks_like_raw_tool_output(content: str) -> bool:
    """Detect if content is raw JSON from search_encik (not generated .enc)."""
    stripped = content.strip()
    if not stripped:
        return True
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
                return True
        except (json.JSONDecodeError, TypeError):
            pass
    return False


def is_raw_tool_output(content: str) -> bool:
    """Check if LLM output is raw JSON echoed from tool calls.

    This is a more permissive check than _looks_like_raw_tool_output
    and is used as a safety net during generation. It catches cases
    where the model outputs tool results verbatim instead of generating
    content, as well as empty or whitespace-only content.

    Args:
        content: LLM response content

    Returns:
        True if content appears to be raw tool output
    """
    if not content or not content.strip():
        return True
    return _looks_like_raw_tool_output(content)
