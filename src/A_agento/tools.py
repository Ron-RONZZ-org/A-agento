"""Tool calling support for A-agento AI commands.

Provides tool definitions and orchestration for LLM tool/function calling.
Currently supports encik database queries for --formato enc generation.

Tool definitions follow OpenAI's tool format for broad compatibility.
"""

from __future__ import annotations

import json
from typing import Any

from A import info
from A.core.providers import LLMProvider, LLMResponse, ToolCall


# ── Tool definitions ─────────────────────────────────────────────────────────
# OpenAI-compatible tool format, also supported by DeepSeek and Ollama 0.5+

SEARCH_ENCIK_TOOL = {
    "type": "function",
    "function": {
        "name": "search_encik",
        "description": "Search the personal encik knowledge base for entries related to a query. Returns title, UUID, and preview.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (title or keyword)",
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

# Combined tools for encik generation
ENCIK_TOOLS = [SEARCH_ENCIK_TOOL, GET_ENTRY_TOOL, WIKIDATA_PROPERTY_TOOL]


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

        sql = f"""SELECT e.uuid, e.titolo, substr(e.difinio, 1, 200) as preview
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
    LIKE search. If the query is a 4-digit year and no results are found,
    automatically creates a year entry and returns its UUID.

    Args:
        query: Search query string

    Returns:
        JSON with matching entries (title, uuid, preview)
    """
    try:
        from A_encik.data.storage import get_db as encik_db
        from A_encik.data.storage import ENCIK_FTS_CONFIG as fts_cfg
        db = encik_db()

        # Try FTS5 first for relevance-ranked results
        results = _search_fts(db, query, fts_cfg)
        if not results:
            # Fallback: LIKE search
            results = db.execute(
                """SELECT uuid, titolo, substr(difinio, 1, 200) as preview
                   FROM encik WHERE titolo LIKE ? OR difinio LIKE ?
                   ORDER BY CASE WHEN titolo LIKE ? THEN 0 ELSE 1 END, titolo
                   LIMIT 8""",
                (f"%{query}%", f"%{query}%", f"{query}%"),
            )
        if results:
            return json.dumps(results, ensure_ascii=False, default=str)

        # No results: if query is a year (CE or BCE), auto-create the entry
        clean = query.strip()
        year = _parse_year(clean)
        if year is not None:
            return _ensure_year_entry(str(year), bce=clean.lower().endswith("bce") or clean.lower().endswith("bc") or "a.k.e" in clean.lower() or "a.k." in clean.lower())

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
        from A_encik.enc_format import entry_to_enc

        db = encik_db()
        entry = db.execute_one(
            "SELECT * FROM encik WHERE uuid LIKE ?", (f"{uuid}%",)
        )
        if entry:
            enc_text = entry_to_enc(entry)
            result = {
                "uuid": entry["uuid"],
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


# Fixed UUIDs for calendar time entries (from user's encik DB)
_YEAR_JARO_UUID = "592e5797"
_YEAR_JARDEKO_UUID = "82064f60"
_YEAR_JARCENTO_UUID = "8677ddbd"
_YEAR_GREGORIA_UUID = "caaf64dc"


def _ensure_or_create(
    titolo: str,
    terminologio_eo: str,
    difino_eo: str,
    superklaso: list[str] | None = None,
) -> str:
    """Find an entry by title or create it. Returns UUID.

    Args:
        titolo: Entry title
        terminologio_eo: Esperanto term
        difino_eo: Definition in Esperanto
        superklaso: Optional parent UUIDs

    Returns:
        UUID string
    """
    from A_encik.service import get_service
    svc = get_service()

    existing = svc.find_by_titolo(titolo)
    if existing:
        return existing["uuid"]

    data = {
        "titolo": titolo,
        "terminologio": {"eo": terminologio_eo},
        "difinoj": {"eo": difino_eo},
    }
    if superklaso:
        data["superklaso"] = superklaso

    entry = svc.create(data)
    return entry["uuid"]


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
    # BCE suffixes
    bce_suffixes = ("bce", "bc", "a.k.e.", "a.k.", "a.K.E.", "a.K.")
    is_bce = any(t.lower().endswith(s.lower()) for s in bce_suffixes)
    if is_bce:
        for s in bce_suffixes:
            if t.lower().endswith(s.lower()):
                t = t[:-len(s)].strip()
                break
    # Now t should be just digits
    if t.isdigit() and 1 <= len(t) <= 4:
        return int(t)
    return None


def _ensure_year_entry(year: str, bce: bool = False) -> str:
    """Create or retrieve calendar time entries for a year.

    Cascading creation: century → decade → year.
    Each level sets the previous as superklaso (parent).
    If entries already exist, returns the existing UUID.

    Args:
        year: Four-digit year string (e.g. "1879")

    Returns:
        JSON with uuid of the year entry
    """
    year_str = year.strip()
    if not year_str.isdigit() or not (1 <= len(year_str) <= 4):
        return json.dumps({"error": f"Invalid year: '{year_str}'. Must be 1-4 digits."})

    try:
        y = int(year_str)
        era_suffix = " a.K.E." if bce else ""
        era_suffix_long = " (a.K.E.)" if bce else ""

        # For BCE centuries/decades, the math is:
        # 44 BCE → century (44-1)//100+1 = 1 → "1a jarcento a.K.E."
        # 3000 BCE → century (3000-1)//100+1 = 30 → "30a jarcento a.K.E."
        # Same formula works for both CE and BCE
        century_num = (y - 1) // 100 + 1
        decade_start = (y // 10) * 10

        # 1. Century
        century_title = f"{century_num}a jarcento{era_suffix_long} (kalendara jarcento)"
        century_term = f"{century_num}a jarcento{era_suffix_long} (kalendara jarcento)"
        century_difino = f"[jarcento](#{_YEAR_JARCENTO_UUID}, rdf:type) de la [Gregoria kalendaro](#{_YEAR_GREGORIA_UUID}, wdt:P361)"
        century_uuid = _ensure_or_create(century_title, century_term, century_difino)

        # 2. Decade
        decade_label = f"{decade_start}a jardeko{era_suffix_long}"
        decade_title = f"{decade_label} (kalendara jardeko)"
        decade_term = f"{decade_label} (kalendara jardeko)"
        decade_difino = f"[jardeko](#{_YEAR_JARDEKO_UUID}, rdf:type) de la [Gregoria kalendaro](#{_YEAR_GREGORIA_UUID}, wdt:P361)"
        decade_uuid = _ensure_or_create(decade_title, decade_term, decade_difino,
                                        superklaso=[century_uuid])

        # 3. Year
        year_label = f"{year_str}{era_suffix}"
        year_title = f"{year_label} (kalendara jaro)"
        year_term = f"{year_label} (kalendara jaro)"
        year_difino = f"[jaro](#{_YEAR_JARO_UUID}, rdf:type) de la [Gregoria kalendaro](#{_YEAR_GREGORIA_UUID}, wdt:P361)"
        year_uuid = _ensure_or_create(year_title, year_term, year_difino,
                                      superklaso=[decade_uuid])

        return json.dumps({"uuid": year_uuid}, ensure_ascii=False, default=str)

    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
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


def _check_user_interject(verbose: bool = False) -> str | None:
    """Pause between turns and let the user type a correction.

    Shows a clear prompt. User can press Enter to continue, or type
    a correction that gets injected into the conversation.

    Returns:
        User's correction string, or None if just continuing
    """
    import sys
    if verbose:
        prompt = "\n[ interjekti: Enter=continue, or type correction and Enter ]\n> "
    else:
        prompt = "\n> "
    sys.stdout.write(prompt)
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
        # Fallback: inject tool results as prompt context
        return _fallback_with_context(provider, messages, tools)

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
            correction = _check_user_interject(verbose=verbose)
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
]
