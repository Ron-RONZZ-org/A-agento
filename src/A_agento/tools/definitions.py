"""Tool definitions for A-agento LLM tool calling.

All tool schemas follow OpenAI's function-calling format for broad
compatibility (DeepSeek, Ollama 0.5+).
"""

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
                    "description": "English keyword describing the property",
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
        "description": "Create or retrieve a calendar century entry. Returns century UUID.",
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

ENCIK_TOOLS = [
    SEARCH_ENCIK_TOOL, GET_ENTRY_TOOL, WIKIDATA_PROPERTY_TOOL,
    ENSURE_DECADE_TOOL, ENSURE_CENTURY_TOOL,
]
