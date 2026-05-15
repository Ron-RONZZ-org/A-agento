"""Tool calling support for A-agento AI commands.

Provides tool definitions and orchestration for LLM tool/function calling.
Currently supports encik database queries for --formato enc generation.

Tool definitions follow OpenAI's tool format for broad compatibility.
"""

from __future__ import annotations

import json
import threading
from typing import Any

from A import info
from A.core.providers import LLMProvider, LLMResponse, ToolCall


# ── Tool definitions ─────────────────────────────────────────────────────────
# OpenAI-compatible tool format, also supported by DeepSeek and Ollama 0.5+

SEARCH_ENCIK_TOOL = {
    "type": "function",
    "function": {
        "name": "search_encik",
        "description": "Search the personal encik knowledge base for entries related to a query. "
                       "Returns title, UUID, and preview. "
                       "For 4-digit year queries (e.g. '1879'), auto-creates the year, decade, "
                       "and century entries — response includes year_uuid, decade_uuid, century_uuid.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (title or keyword). "
                                   "4-digit numbers auto-create time entries.",
                }
            },
            "required": ["query"],
        },
    },
}

GET_ENTRY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_encik_entry",
        "description": "Get a full encik entry by UUID, including all fields and semantic links.",
        "parameters": {
            "type": "object",
            "properties": {
                "uuid": {
                    "type": "string",
                    "description": "Full or prefix UUID of the entry",
                }
            },
            "required": ["uuid"],
        },
    },
}

WIKIDATA_PROPERTY_TOOL = {
    "type": "function",
    "function": {
        "name": "wikidata_property_id",
        "description": "Search for a Wikidata property ID by English keyword. "
                       "Use ENGLISH keywords only (the cache and Wikidata descriptions "
                       "are primarily in English). "
                       "Example: 'profession' returns wdt:P106, 'date of birth' returns wdt:P569. "
                       "Returns ALL matching properties so you can choose the correct one.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "English keyword describing the property (e.g. 'profession', 'date of birth', 'country')",
                }
            },
            "required": ["query"],
        },
    },
}

ENSURE_DECADE_TOOL = {
    "type": "function",
    "function": {
        "name": "ensure_decade",
        "description": "Create or retrieve a calendar decade entry and its parent century. "
                       "Returns decade UUID and century UUID.",
        "parameters": {
            "type": "object",
            "properties": {
                "decade": {
                    "type": "string",
                    "description": "Decade start year, must be multiple of 10 (e.g. '1780' for the 1780s)",
                },
                "bce": {
                    "type": "boolean",
                    "description": "True for BCE (before Common Era)",
                    "default": False,
                },
            },
            "required": ["decade"],
        },
    },
}

ENSURE_CENTURY_TOOL = {
    "type": "function",
    "function": {
        "name": "ensure_century",
        "description": "Create or retrieve a calendar century entry. "
                       "Returns century UUID.",
        "parameters": {
            "type": "object",
            "properties": {
                "century": {
                    "type": "string",
                    "description": "Century number (e.g. '18' for the 18th century)",
                },
                "bce": {
                    "type": "boolean",
                    "description": "True for BCE (before Common Era)",
                    "default": False,
                },
            },
            "required": ["century"],
        },
    },
}

# Combined tools for encik generation
ENCIK_TOOLS = [
    SEARCH_ENCIK_TOOL, GET_ENTRY_TOOL, WIKIDATA_PROPERTY_TOOL,
    ENSURE_DECADE_TOOL, ENSURE_CENTURY_TOOL,
]


# ── Tool execution ───────────────────────────────────────────────────────────


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


def _search_fts(db, query: str, fts_cfg) -> list[dict] | None:
    """Search encik DB using FTS5 for relevance-ranked results.

    Args:
        db: SQLiteDB instance
        query: Search query string
        fts_cfg: FTSConfig from A_encik

    Returns:
        List of matching entries or None if FTS fails
    """
    try:
        # Convert query to FTS5 MATCH format: escape special chars, add prefix
        import re as _re
        terms = _re.findall(r"[a-zA-Z0-9]+", query)
        if not terms:
            return None
        fts_query = " OR ".join(f"{t}*" for t in terms[:5])

        # Note: e.titolo is still in the schema (transition period),
        # but terminologio is the canonical title source
        sql = f"""SELECT e.uuid, e.terminologio, substr(e.difinio, 1, 200) as preview
                  FROM encik e
                  JOIN {fts_cfg.fts_table} f ON e.rowid = f.rowid
                  WHERE {fts_cfg.fts_table} MATCH ?
                  ORDER BY rank
                  LIMIT 8"""
        return db.execute(sql, (fts_query,))
    except Exception:
        return None


def _search_encik(query: str) -> str:
    """Search encik DB by keyword/title.

    Uses FTS5 for relevance-ranked results when available, falls back to
    LIKE search. If the query is a 1-4 digit number, short-circuits to
    auto-create the year entry (and its decade/century parents) without
    hitting DB search. Response includes ``decade_uuid`` and
    ``century_uuid`` when applicable.

    Args:
        query: Search query string

    Returns:
        JSON with matching entries (title, uuid, preview)
    """
    try:
        # If query is a year, short-circuit — create/retrieve year entry directly
        clean = query.strip()
        year = _parse_year(clean)
        if year is not None:
            bce = clean.lower().endswith("bce") or clean.lower().endswith("bc") or "a.k.e" in clean.lower() or "a.k." in clean.lower()
            return _ensure_year_entry(str(year), bce=bce)

        from A_encik.data.storage import get_db as encik_db
        from A_encik.data.storage import ENCIK_FTS_CONFIG as fts_cfg
        db = encik_db()

        # Try FTS5 first for relevance-ranked results
        results = _search_fts(db, query, fts_cfg)
        if not results:
            # Fallback: LIKE search
            results = db.execute(
                """SELECT uuid, terminologio, substr(difinio, 1, 200) as preview
                   FROM encik WHERE terminologio LIKE ? OR difinio LIKE ?
                   ORDER BY CASE WHEN terminologio LIKE ? THEN 0 ELSE 1 END
                   LIMIT 8""",
                (f"%{query}%", f"%{query}%", f"{query}%"),
            )
        if results:
            # Truncate UUIDs to 8 chars so LLM uses prefixes, not full UUIDs
            for r in results:
                if "uuid" in r and len(r["uuid"]) > 8:
                    r["uuid"] = r["uuid"][:8]
            return json.dumps(results, ensure_ascii=False, default=str)

        return json.dumps({"message": f"No entries found for '{query}'"})
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})


def _get_encik_entry(uuid: str) -> str:
    """Get a full encik entry by UUID.

    Args:
        uuid: Entry UUID (full or prefix)

    Returns:
        JSON with the full entry
    """
    try:
        from A_encik.data.storage import get_db as encik_db
        from A_encik.data.storage import row_to_dict
        from A_encik.enc_format import entry_to_enc

        db = encik_db()
        entry = db.execute_one(
            "SELECT * FROM encik WHERE uuid LIKE ?", (f"{uuid}%",)
        )
        if entry:
            # Deserialize JSON fields before passing to entry_to_enc
            entry = row_to_dict(entry)
            enc_text = entry_to_enc(entry)
            result = {
                "uuid": entry["uuid"][:8],
                "titolo": entry["titolo"],
                "enc_format": enc_text[:2000],
            }
            return json.dumps(result, ensure_ascii=False, default=str)
        return json.dumps({"error": f"No entry found for UUID '{uuid}'"})
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Wikidata property lookup ─────────────────────────────────────────────────


def _lookup_wikidata_property(query: str) -> str:
    """Search for Wikidata properties by English keyword.

    Always queries in English for consistency. Delegates to A-encik's
    semantika_cache which handles: SQLite cache → CSV files → Wikidata API.

    Args:
        query: English keyword (e.g. "profession", "date of birth")

    Returns:
        JSON with results array or error message
    """
    if not query or not query.strip():
        return json.dumps({"results": [], "message": "Empty query"})

    try:
        from A_encik.data.semantika_cache import lookup_property
        result = lookup_property(query.strip())
        return json.dumps(result, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed. Cannot query Wikidata properties."})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Year entry management ────────────────────────────────────────────────────


def _parse_year(text: str) -> int | None:
    """Parse a year string (CE or BCE) into a positive integer.

    Accepts:
    - "1879" → 1879 (CE)
    - "44 BCE", "44 BC", "44 bce", "44 bc" → 44
    - "44 a.K.E.", "44 a.k.e." → 44
    - "3000 BCE" → 3000
    - "1000" → 1000

    Returns the numeric year (always positive), or None if not a valid year.
    """
    t = text.strip()
    bce_suffixes = ("bce", "bc", "a.k.e.", "a.k.", "a.K.E.", "a.K.")
    is_bce = any(t.lower().endswith(s.lower()) for s in bce_suffixes)
    if is_bce:
        for s in bce_suffixes:
            if t.lower().endswith(s.lower()):
                t = t[:-len(s)].strip()
                break
    if t.isdigit() and 1 <= len(t) <= 4:
        return int(t)
    return None


def _ensure_year_entry(year: str, bce: bool = False) -> str:
    """Create or retrieve calendar time entries for a year.

    Delegates to A-encik's centralized ``EncikService.ensure_year()``,
    which cascades: century → decade → year.

    Returns ALL three UUIDs so the LLM can reference the year, its
    decade, or its century as needed.

    Args:
        year: Year string (1-4 digits, e.g. "1879")

    Returns:
        JSON with ``year_uuid``, ``decade_uuid``, ``century_uuid``
    """
    year_str = year.strip()
    if not year_str.isdigit() or not (1 <= len(year_str) <= 4):
        return json.dumps({"error": f"Invalid year: '{year_str}'. Must be 1-4 digits."})

    try:
        from A_encik.service import get_service
        svc = get_service()
        y = int(year_str)
        era_short, era_long = (" a.K.E.", " (a.K.E.)") if bce else ("", "")

        # ensure_year creates century → decade → year cascade
        entry = svc.ensure_year(y, bce=bce)

        # Look up decade and century by their known titolo patterns
        decade_start = (y // 10) * 10
        century_num = (y - 1) // 100 + 1

        decade_titolo = f"{decade_start}a jardeko{era_long} (kalendara jardeko)"
        decade = svc.find_by_titolo(decade_titolo)

        century_titolo = f"{century_num}a jarcento{era_long} (kalendara jarcento)"
        century = svc.find_by_titolo(century_titolo)

        result: dict[str, str] = {"uuid": entry["uuid"][:8]}
        if decade:
            result["decade_uuid"] = decade["uuid"][:8]
        if century:
            result["century_uuid"] = century["uuid"][:8]

        return json.dumps(result, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _ensure_decade_entry(decade: str, bce: bool = False) -> str:
    """Create or retrieve a decade entry and its parent century.

    Args:
        decade: Decade start year (multiple of 10, e.g. "1780")

    Returns:
        JSON with ``uuid``, ``century_uuid``
    """
    d = decade.strip()
    if not d.isdigit():
        return json.dumps({"error": f"Invalid decade: '{d}'. Must be a number."})
    dv = int(d)
    if dv % 10 != 0:
        return json.dumps({"error": f"Invalid decade: '{d}'. Must be a multiple of 10 (e.g. 1780)."})

    try:
        from A_encik.service import get_service
        svc = get_service()
        entry = svc.ensure_decade(dv, bce=bce)
        era_short, era_long = (" a.K.E.", " (a.K.E.)") if bce else ("", "")
        century_num = (dv - 1) // 100 + 1
        century_titolo = f"{century_num}a jarcento{era_long} (kalendara jarcento)"
        century = svc.find_by_titolo(century_titolo)
        result: dict[str, str] = {"uuid": entry["uuid"][:8]}
        if century:
            result["century_uuid"] = century["uuid"][:8]
        return json.dumps(result, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _ensure_century_entry(century: str, bce: bool = False) -> str:
    """Create or retrieve a century entry.

    Args:
        century: Century number (e.g. "18" for the 18th century)

    Returns:
        JSON with ``uuid``
    """
    c = century.strip()
    if not c.isdigit():
        return json.dumps({"error": f"Invalid century: '{c}'. Must be a number."})

    try:
        from A_encik.service import get_service
        svc = get_service()
        entry = svc.ensure_century(int(c), bce=bce)
        return json.dumps({"uuid": entry["uuid"][:8]}, ensure_ascii=False, default=str)
    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Output validation ────────────────────────────────────────────────────────


def _looks_like_raw_tool_output(content: str) -> bool:
    """Detect if LLM output is raw JSON echoed from search_encik tool.

    Checks for JSON array format with uuid/titolo keys, which indicates
    the model failed to generate proper content and just echoed the tool result.

    Args:
        content: LLM response content

    Returns:
        True if content looks like raw tool output
    """
    stripped = content.strip()
    if not stripped:
        return False
    # Check for JSON array starting with [ and containing uuid/titolo
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            data = json.loads(stripped)
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict) and "uuid" in first and "titolo" in first:
                    return True
        except (json.JSONDecodeError, TypeError, IndexError):
            pass
    # Check for single JSON object with uuid (e.g. year auto-creation result)
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and "uuid" in data and "titolo" not in data:
                return True  # Year creation result like {"uuid": "..."}
        except (json.JSONDecodeError, TypeError):
            pass
    return False


# ── Output validation ────────────────────────────────────────────────────────


def is_raw_tool_output(content: str) -> bool:
    """Detect if LLM output is raw JSON echoed from tool results.

    Any valid JSON that isn't .enc content is tool output.
    Safe because generate_with_tools is only called for --formato enc,
    and .enc files never start with [ or {.

    Args:
        content: LLM response content

    Returns:
        True if content looks like raw tool output
    """
    stripped = content.strip()
    if not stripped:
        return True
    if (stripped.startswith("[") and stripped.endswith("]")) or \
       (stripped.startswith("{") and stripped.endswith("}")):
        try:
            json.loads(stripped)
            return True
        except (json.JSONDecodeError, TypeError):
            pass
    return False


# ── Orchestration ────────────────────────────────────────────────────────────


_pause_requested = threading.Event()
_pause_listener = None


def _key_listener():
    """Daemon thread: reads single chars from stdin, sets flag on 'x'."""
    import sys
    try:
        while True:
            ch = sys.stdin.read(1)
            if ch == 'x':
                _pause_requested.set()
    except (EOFError, OSError):
        pass


def _ensure_listener():
    """Start the daemon listener once."""
    global _pause_listener
    if _pause_listener is None or not _pause_listener.is_alive():
        _pause_listener = threading.Thread(target=_key_listener, daemon=True)
        _pause_listener.start()


def _check_user_interject() -> str | None:
    """Check if 'x' was pressed. If so, pause for user correction.

    Returns user input, or None if 'x' wasn't pressed.
    """
    if not _pause_requested.is_set():
        return None
    _pause_requested.clear()

    import sys
    sys.stdout.write("\n[PAUSED — type correction and press Enter, or just Enter to continue]\n> ")
    sys.stdout.flush()
    line = sys.stdin.readline().strip()
    return line if line else None


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
            _v(f"\n── [{role}] ──")
            if content:
                _v(content[:8000])
            if rc:
                _v(f"\n[Reasoning]: {rc[:1000]}")

    if not provider.supports_tools:
        return _fallback_with_context(provider, messages, tools)

    if interject:
        from A import info as _hint
        _hint("Press 'x' at any time to pause and type a correction")

    for turn in range(max_turns):
        response = provider.chat(messages, tools=tools)

        if verbose:
            from A.utils import info as _v
            _v(f"\n── [ASSISTANT (turn {turn+1})] ──")
            if response.content:
                _v(response.content[:8000])
            if response.reasoning_content:
                _v(f"\n[Reasoning]: {response.reasoning_content[:4000]}")
            if response.tool_calls:
                for tc in response.tool_calls:
                    _v(f"\n  TOOL CALL: {tc.function.get('name', '?')}")
                    _v(f"     args: {tc.function.get('arguments', '{}')[:500]}")

        if interject:
            _ensure_listener()
            correction = _check_user_interject()
            if correction:
                messages.append({
                    "role": "user",
                    "content": f"[User correction]: {correction}"
                })
                if verbose:
                    _v(f"\n  [USER CORRECTION]: {correction}")

        if not response.tool_calls:
            # Check for raw tool output echoed by the model
            if is_raw_tool_output(response.content):
                if verbose:
                    _v("\n[WARNING] Raw tool output detected, retrying...")
                messages.append({
                    "role": "user",
                    "content": "That was tool result data. Now generate the actual content in the requested format, no extra explanation, no code fences."
                })
                continue
            return response.content  # Valid final response — no more tool calls

        # Add assistant message with tool calls
        # Preserve reasoning_content (DeepSeek thinking mode requires echo)
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content}
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
                _v(f"\n  TOOL RESULT ({tc.function.get('name', '?')}):")
                _v(f"     {result[:600]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        # Doomloop detection: same tool call 3+ times -> break the loop
        _tool_call_history: dict[str, int] = getattr(
            generate_with_tools, "_tool_hist", {}
        )
        for tc in response.tool_calls:
            sig = f"{tc.function.get('name', '')}|{tc.function.get('arguments', '')}"
            _tool_call_history[sig] = _tool_call_history.get(sig, 0) + 1
        generate_with_tools._tool_hist = _tool_call_history
        if any(c >= 3 for c in _tool_call_history.values()):
            if verbose:
                _v("\n[WARNING] Repeated tool calls detected, forcing generation...")
            messages.append({
                "role": "user",
                "content": "You have been repeating tool calls. Stop now and generate the content based on what you already have."
            })
            continue

    # Max turns reached — force one final generation without tools
    if verbose:
        from A.utils import info as _v
        _v("\n── [FORCED FINAL GENERATION] ──")
    final_response = provider.chat(messages)  # No tools
    final_content = final_response.content or ""
    if verbose and final_content:
        _v(final_content[:2000])
    if final_content and not is_raw_tool_output(final_content):
        return final_content
    return ""  # Complete failure


def _fallback_with_context(
    provider: LLMProvider,
    messages: list[dict],
    tools: list[dict],
) -> str:
    """Fallback: pre-search encik DB and inject context into prompt.

    Used when the provider doesn't support native tool calling.
    Extracts keywords from the user message, searches encik DB,
    and injects results as context.

    Args:
        provider: LLM provider
        messages: Chat messages
        tools: Tool definitions (used to extract search terms)

    Returns:
        Generated text
    """
    import re

    # Extract user's last message content
    user_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break

    # Simple keyword extraction
    keywords = re.findall(r"\b[a-zA-Z]{4,}\b", user_content)
    keywords = list(dict.fromkeys(k.lower() for k in keywords))[:3]

    if keywords:
        context_parts = []
        for kw in keywords:
            result = _search_encik(kw)
            data = json.loads(result)
            if isinstance(data, list) and data:
                for entry in data[:3]:
                    context_parts.append(
                        f"- {entry.get('titolo', '?')} (#{entry.get('uuid', '?')[:8]})"
                    )
        if context_parts:
            context = "\n".join(context_parts[:5])
            messages.insert(0, {
                "role": "system",
                "content": f"Related entries in your knowledge base:\n{context}\n\nYou can reference these entries using [title](#uuid) syntax in your response.",
            })

    prompt = "\n".join(
        f"{m.get('role', '')}: {m.get('content', '')}" for m in messages
    )
    return provider.generate(prompt)


__all__ = [
    "ENCIK_TOOLS",
    "execute_tool_call",
    "generate_with_tools",
    "ENSURE_DECADE_TOOL",
    "ENSURE_CENTURY_TOOL",
]
