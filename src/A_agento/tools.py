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


def _search_encik(query: str) -> str:
    """Search encik DB by keyword/title.

    If the query is a 4-digit year and no results are found, automatically
    creates a year entry and returns its UUID. This eliminates the need for
    the LLM to call a separate tool for year entries.

    Args:
        query: Search query string

    Returns:
        JSON with matching entries (title, uuid, preview)
    """
    try:
        from A_encik.data.storage import get_db as encik_db
        db = encik_db()
        results = db.execute(
            """SELECT uuid, titolo, substr(difinio, 1, 200) as preview
               FROM encik WHERE titolo LIKE ?
               ORDER BY CASE WHEN titolo LIKE ? THEN 0 ELSE 1 END, titolo
               LIMIT 8""",
            (f"%{query}%", f"{query}%"),
        )
        if results:
            return json.dumps(results, ensure_ascii=False, default=str)

        # No results: if query is a 4-digit year, auto-create the entry
        clean = query.strip()
        if clean.isdigit() and len(clean) == 4:
            return _ensure_year_entry(clean)

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


def _ensure_year_entry(year: str) -> str:
    """Create or retrieve calendar time entries for a year.

    Cascading creation: century → decade → year.
    Each level sets the previous as superklaso (parent).
    If entries already exist, returns the existing UUID.

    Args:
        year: Four-digit year string (e.g. "1879")

    Returns:
        JSON with uuid of the year entry
    """
    year = year.strip()
    if not year.isdigit() or len(year) != 4:
        return json.dumps({"error": f"Invalid year: '{year}'. Must be 4 digits."})

    try:
        y = int(year)
        century_num = (y - 1) // 100 + 1  # 1879 → 19th century
        decade_start = (y // 10) * 10      # 1879 → 1870s

        # 1. Century: e.g. "19a jarcento (kalendara jarcento)"
        century_id = f"{century_num}a jarcento"
        century_title = f"{century_num}a jarcento (kalendara jarcento)"
        century_term = f"{century_num}a jarcento (kalendara jarcento)"
        century_difino = f"[jarcento](#{_YEAR_JARCENTO_UUID}, rdf:type) de la [Gregoria kalendaro](#{_YEAR_GREGORIA_UUID}, wdt:P361)"
        century_uuid = _ensure_or_create(century_title, century_term, century_difino)

        # 2. Decade: e.g. "1870a jardeko (kalendara jardeko)"
        decade_label = f"{decade_start}a jardeko"
        decade_title = f"{decade_label} (kalendara jardeko)"
        decade_term = f"{decade_label} (kalendara jardeko)"
        decade_difino = f"[jardeko](#{_YEAR_JARDEKO_UUID}, rdf:type) de la [Gregoria kalendaro](#{_YEAR_GREGORIA_UUID}, wdt:P361)"
        decade_uuid = _ensure_or_create(decade_title, decade_term, decade_difino,
                                        superklaso=[century_uuid])

        # 3. Year: e.g. "1879 (kalendara jaro)"
        year_title = f"{year} (kalendara jaro)"
        year_term = f"{year} (kalendara jaro)"
        year_difino = f"[jaro](#{_YEAR_JARO_UUID}, rdf:type) de la [Gregoria kalendaro](#{_YEAR_GREGORIA_UUID}, wdt:P361)"
        year_uuid = _ensure_or_create(year_title, year_term, year_difino,
                                      superklaso=[decade_uuid])

        return json.dumps({"uuid": year_uuid}, ensure_ascii=False, default=str)

    except ImportError:
        return json.dumps({"error": "A-encik is not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Orchestration ────────────────────────────────────────────────────────────


def generate_with_tools(
    provider: LLMProvider,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_turns: int = 5,
    verbose: bool = False,
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
                _v(content[:2000])
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
                _v(response.content[:2000])
            if response.reasoning_content:
                _v(f"\n[Reasoning]: {response.reasoning_content[:1000]}")

        if not response.tool_calls:
            return response.content  # Final response — no more tool calls

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
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # Max turns reached — return last assistant content
    return messages[-1].get("content", "") if messages else ""


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
