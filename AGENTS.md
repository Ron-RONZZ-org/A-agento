# AGENTS.md — Rules for A-agento

This file extends [root AGENTS.md](../AGENTS.md).

## Relationship to A-core

**A-agento depends on A-core** for:
- `A` package imports (i18n, output, subprocess, SQLite)
- Plugin discovery via entry points
- **A.core.ai**: LLM provider abstraction (get_provider, save_api_key, LLMProvider)
- Shared utilities

**All source code must import from `A`, never duplicate utilities.**

## Module Purpose

A-agento provides AI-powered email assistance:
- Email summarization
- Smart reply draft generation
- Action extraction (calendar events, todos, knowledge entries)

## Cross-Module Dependencies

A-agento integrates with (runtime detection):
- **A-lien**: Email access (RetpostoService for messages)
- **A-organizi**: Calendar events (EventService), todos (TodoService)
- **A-encik**: Knowledge entries (EncikService)

All cross-module imports use try/except with graceful fallback.

## Architecture

```
src/A_agento/
├── __init__.py       # exports: app
├── cli.py           # Typer app with commands
├── service.py      # AgentService orchestration
├── prompts.py    # Prompt templates
└── data/
    └── storage.py # SQLite for agent metadata
```

## Security Rules

1. **API key storage**: OpenAI key stored in system keyring (never SQLite)
2. **Confirmation gate**: All AI-suggested write actions require user confirmation
3. **Privacy**: User chooses provider; Ollama = fully local
4. **Input validation**: Sanitize prompts before sending to LLM

## Confirmation Gate Pattern

```python
from A import info, tr_multi
import typer

def _confirm_action(description: str) -> bool:
    """Show action preview and ask user to confirm."""
    info(f"Proponita ago: {description}")
    result = typer.confirm(tr_multi("Ĉu plenumi?", "Execute?", "Exécuter?"))
    if not result:
        info(tr("Nuligita."))
        return False
    return True
```

## What to Avoid

- Don't auto-execute AI-suggested writes without confirmation
- Don't hardcode provider — use A.core.ai.get_provider()
- Don't duplicate A-core utilities
- Don't skip i18n (use tr_multi() / tr())
- Don't use print() — use A output functions