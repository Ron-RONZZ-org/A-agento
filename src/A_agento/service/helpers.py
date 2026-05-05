"""Helper types and utilities for AgentService.

- _extract_json: Parse JSON from LLM responses (handles markdown fences)
- EmailSummary: Structured summary result
- ActionSuggestion: Parsed action suggestion from email
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response (handles markdown fences, leading text).

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    import re

    # Try to find ```json ... ``` block first
    if match := re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL):
        text = match.group(1)

    # Remove any leading/trailing non-JSON text
    text = text.strip()

    # Try direct parse
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Last resort: find first { and last }
    if (start := text.find("{")) != -1 and (end := text.rfind("}")) != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


@dataclass
class EmailSummary:
    """Summarized email."""

    uuid: str
    sender: str
    recipients: str
    subject: str
    body: str
    summary: str
    received_at: str


@dataclass
class ActionSuggestion:
    """Extracted action from email."""

    action_type: str  # "calendar", "todo", "knowledge"
    title: str
    details: str
    metadata: dict[str, Any]


__all__ = [
    "_extract_json",
    "EmailSummary",
    "ActionSuggestion",
]
