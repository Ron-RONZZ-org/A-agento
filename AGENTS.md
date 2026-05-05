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
├── __init__.py             # exports: app
├── cli.py                 # Typer app (resumu, respondi, agu, generi)
├── agordo.py              # Provider config sub-app (default, sxlosilo, montri, testi)
├── stilo.py               # Style sample sub-app (aldoni, listo, forigu, aktiva)
├── registration.py        # AI sub-app factories for cross-module injection
├── service.py             # AgentService orchestration
├── prompts.py             # Prompt templates
├── contract.py            # Service contract with A-lien
├── commands/
│   ├── __init__.py
│   ├── _helpers.py         # Shared helpers (get_provider_or_exit, confirm_action)
│   ├── email.py            # resumu, respondi, agu
│   └── knowledge.py        # generi (moved from A-encik)
└── data/
    ├── __init__.py
    ├── storage.py          # SQLite for agent metadata + history + styloj
    └── provider_config.py  # Provider metadata storage (non-secret config)
```

### Cross-Module AI Injection

A-agento registers AI commands for compatible A-modules via the `A.ai_commands` entry point group. A-core's `plugin_loader` (`A.core.plugin_loader`) discovers these on first use and injects them as `ai` sub-apps:

| Module   | AI Commands                 | Entry point                      |
|----------|-----------------------------|----------------------------------|
| A-lien   | resumu, respondi, agu       | `A_agento.registration:get_lien_ai_app` |
| A-encik  | generi                      | `A_agento.registration:get_encik_ai_app` |

This creates a separate `ai` section in the module's help output:

```
$ A retposto --help
╭─ retposto ────────────────────────────────────────────────────╮
│ sendi      Send emails                                        │
│ preni      Fetch emails                                       │
╰───────────────────────────────────────────────────────────────╯
╭─ ai ──────────────────────────────────────────────────────────╮
│ resumu     Summarize emails (AI via A-agento)                 │
│ respondi   Generate smart reply (AI via A-agento)             │
╰───────────────────────────────────────────────────────────────╯
```

### Sub-app Groups

- `agento agordo` — Provider configuration (default, sxlosilo, montri, testi)
- `agento stilo` — Writing style samples (aldoni, listo, forigu, aktiva)

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