"""Tool execution and multi-turn generation orchestration for A-agento."""

from __future__ import annotations

import json
import sys
import threading
from typing import Any

from A import info
from A.core.providers import LLMProvider, LLMResponse, ToolCall

from A_agento.tools.definitions import ENCIK_TOOLS
from A_agento.tools.search import (
    _search_encik,
    _get_encik_entry,
    _lookup_wikidata_property,
)
from A_agento.tools.years import (
    _ensure_decade_entry,
    _ensure_century_entry,
)
from A_agento.tools.cleaners import _looks_like_raw_tool_output


_SNIPPET_CHARS = 200  # chars of first/last snippet shown in verbose mode


def _summarize_content(content: str) -> str:
    """Format content for verbose display: full if short, else size + snippets.

    Args:
        content: The message content to display.

    Returns:
        Formatted string for terminal output.
    """
    size = len(content)
    if size <= _SNIPPET_CHARS * 2:
        return content
    first = content[:_SNIPPET_CHARS].replace("\n", "\\n")
    last = content[-_SNIPPET_CHARS:].replace("\n", "\\n")
    return (
        f"📎 {size:,} chars  —  first {_SNIPPET_CHARS}: \"{first}\""
        f"\n  …  last {_SNIPPET_CHARS}:  \"{last}\""
    )


def execute_tool_call(tool_call: ToolCall) -> str:
    """Execute a tool call and return the result as JSON string.

    Args:
        tool_call: ToolCall with name and arguments

    Returns:
        JSON-serialized result string
    """
    name = tool_call.function.get("name", "")
    args_raw = tool_call.function.get("arguments", "{}")
    try:
        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
    except json.JSONDecodeError:
        return json.dumps({"error": f"Invalid arguments JSON: {args_raw}"})

    if name == "search_encik":
        return _search_encik(args.get("query", ""))
    elif name == "get_encik_entry":
        return _get_encik_entry(args.get("uuid", ""))
    elif name == "wikidata_property_id":
        return _lookup_wikidata_property(args.get("query", ""))
    elif name == "ensure_decade":
        return _ensure_decade_entry(
            args.get("decade", ""),
            bce=bool(args.get("bce", False)),
        )
    elif name == "ensure_century":
        return _ensure_century_entry(
            args.get("century", ""),
            bce=bool(args.get("bce", False)),
        )
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# ── Interrupt listener (threaded) ──────────────────────────────────


_listener_started = False
_last_user_input: str | None = None
_input_lock = threading.Lock()


def _key_listener() -> None:
    """Background thread: listen for 'x' to pause and type a correction."""
    global _last_user_input
    while True:
        try:
            ch = sys.stdin.read(1)
            if ch == "x":
                with _input_lock:
                    _last_user_input = (
                        "x"  # Signal that user wants to interject
                    )
        except (EOFError, OSError):
            break


def _ensure_listener() -> None:
    """Start the background key listener thread (once)."""
    global _listener_started
    if not _listener_started:
        _listener_started = True
        t = threading.Thread(target=_key_listener, daemon=True)
        t.start()


def _check_user_interject() -> str | None:
    """Check if user pressed 'x' to interject. Returns correction or None."""
    global _last_user_input, _input_lock
    with _input_lock:
        if _last_user_input == "x":
            from A import info as _hint

            _hint(
                "\n[Type your correction/prompt, then press Enter. "
                "Leave empty to continue.]"
            )
            correction = sys.stdin.readline().strip()
            _last_user_input = None
            return correction if correction else None
        return None


# ── Multi-turn generation ──────────────────────────────────────────


def generate_with_tools(
    provider: LLMProvider,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_turns: int = 30,
    verbose: bool = False,
    interject: bool = False,
) -> str:
    """Multi-turn generation with tool calling support.

    If the provider doesn't support tools, falls back to prompt-injection.

    Args:
        provider: LLM provider instance
        messages: Initial chat messages
        tools: Tool definitions (optional, uses ENCIK_TOOLS by default)
        max_turns: Maximum tool call rounds
        verbose: If True, print full conversation to terminal

    Returns:
        Generated text content
    """
    if tools is None:
        tools = ENCIK_TOOLS

    if verbose:
        from A.utils import info as _v

        _v("\n═══════ LLM Conversation Start ═══════")
        for msg in messages:
            role = msg.get("role", "?").upper()
            content = msg.get("content", "")
            rc = msg.get("reasoning_content", "")
            display_hint = msg.get("_display_hint", "")
            _v(f"\n── [{role}] ──")
            if content:
                if display_hint == "external_context":
                    _v(_summarize_content(content))
                else:
                    _v(content)
            if rc:
                _v(f"\n[Reasoning]: {_summarize_content(rc)}")

    if not provider.supports_tools:
        return _fallback_with_context(provider, messages, tools)

    if interject:
        from A import info as _hint

        _hint("Press 'x' at any time to pause and type a correction")

    # Strip display-only metadata before sending to LLM
    _clean_messages = []
    for m in messages:
        clean = {k: v for k, v in m.items() if not k.startswith("_")}
        _clean_messages.append(clean)
    messages = _clean_messages

    raw_output_retries = 0

    for turn in range(max_turns):
        response = provider.chat(messages, tools=tools)

        if verbose:
            from A.utils import info as _v

            _v(f"\n── [ASSISTANT (turn {turn+1})] ──")
            if response.content:
                _v(_summarize_content(response.content))
            if response.reasoning_content:
                _v(f"\n[Reasoning]: {_summarize_content(response.reasoning_content)}")
            if response.tool_calls:
                for tc in response.tool_calls:
                    _v(f"\n  TOOL CALL: {tc.function.get('name', '?')}")
                    _v(f"     args: {tc.function.get('arguments', '{}')[:500]}")

        if interject:
            _ensure_listener()
            correction = _check_user_interject()
            if correction:
                messages.append(
                    {
                        "role": "user",
                        "content": f"[User correction]: {correction}",
                    }
                )
                if verbose:
                    _v(f"\n  [USER CORRECTION]: {correction}")

        if not response.tool_calls:
            if is_raw_tool_output(response.content):
                raw_output_retries += 1
                if verbose:
                    _v(f"\n[WARNING] Raw tool output detected (attempt {raw_output_retries}), retrying...")

                # Escalating retry messages
                retry_messages = [
                    # 1st attempt — polite hint
                    "That was tool result data. Now generate the actual content "
                    "in the requested format, no extra explanation, no code fences.",
                    # 2nd attempt — stronger hint
                    "You are outputting raw search results. Generate the final content now. "
                    "Use your existing knowledge. Omit links for unknown entities.",
                    # 3rd+ attempt — direct command
                    "STOP searching. Generate the output now using what you know. "
                    "No more tools. Output the result directly.",
                ]
                idx = min(raw_output_retries - 1, len(retry_messages) - 1)
                messages.append({"role": "user", "content": retry_messages[idx]})
                continue
            return response.content

        # Add assistant message with tool calls
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.content,
        }
        if response.reasoning_content:
            assistant_msg["reasoning_content"] = response.reasoning_content
        assistant_msg["tool_calls"] = [
            {"id": tc.id, "type": tc.type, "function": tc.function}
            for tc in response.tool_calls
        ]
        messages.append(assistant_msg)

        # Execute each tool call and add result
        for tc in response.tool_calls:
            result = execute_tool_call(tc)
            if verbose:
                from A.utils import info as _v

                _v(f"\n  TOOL RESULT ({tc.function.get('name', '?')}):")
                _v(f"     {result[:600]}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    # ── Exhausted max_turns: force final generation without tools ──
    if verbose:
        from A.utils import info as _v
        _v(f"\n[WARNING] max_turns={max_turns} exhausted. Forcing final generation...")

    content = ""
    if response and response.tool_calls:
        # Last response had tool_calls — force a final answer without tool access
        messages.append({
            "role": "user",
            "content": (
                "You have exhausted all search attempts. "
                "Now generate the final output immediately using your existing knowledge. "
                "Do not search again. Do not call any tools."
            ),
        })
        final_response = provider.chat(messages, tools=None)
        if final_response and final_response.content:
            content = final_response.content
    elif response and response.content:
        content = response.content

    # Safety net: if content is still empty or raw tool output, try one more forceful call
    if not content or is_raw_tool_output(content):
        messages.append({
            "role": "user",
            "content": (
                "You must generate the final content now. "
                "No more tool calls. Output the result directly."
            ),
        })
        final_response = provider.chat(messages, tools=None)
        if final_response and final_response.content:
            content = final_response.content

    return content


def _fallback_with_context(
    provider: LLMProvider,
    messages: list[dict],
    tools: list[dict],
) -> str:
    """Fallback for providers that don't support tool calling.

    Injects tool descriptions and context into the system message
    so the LLM can reason about what to search for, even if it
    can't actually call tools.

    Args:
        provider: LLM provider
        messages: Chat messages
        tools: Tool definitions (for context injection)

    Returns:
        Generated text
    """
    tool_descriptions = "\n".join(
        f"- {t['function']['name']}: {t['function']['description']}"
        for t in tools
    )
    context = (
        "\n\nYou have access to the following tools (simulate their use "
        "in your response):\n" + tool_descriptions
    )

    if messages and messages[0].get("role") == "system":
        messages[0]["content"] += context
    else:
        messages.insert(0, {"role": "system", "content": context})

    return provider.chat(messages).content


# Avoid circular: cleaners.py is a leaf module
from A_agento.tools.cleaners import is_raw_tool_output  # noqa: E402, F401
