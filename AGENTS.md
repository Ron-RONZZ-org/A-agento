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

A-agento provides the general LLM interface — direct text operations (generation,
translation) and AI-powered assistance for other A-modules (email, calendar,
knowledge):

- **General LLM**: text generation (`generi`), text translation (`traduki`)
- **Email-specific**: summarization (`resumu`), smart reply (`respondi`),
  action extraction (`agu`) — requires A-lien
- **Cross-module AI injection**: AI commands injected into A-lien, A-encik
  via `A.ai_commands` entry points

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
├── cli.py                 # Typer app (resumu, respondi, agu, generi, traduki, plibonigi)
├── agordo.py              # Provider config sub-app (default, aldoni, ls, testi)
├── stilo.py               # Style sample sub-app (aldoni, listo, forigu, aktiva)
├── provider_state.py      # Fallback order management (prioritato-based)
├── registration.py        # AI sub-app factories for cross-module injection
├── service.py             # AgentService orchestration
├── prompts.py             # Prompt templates
├── contract.py            # Service contract with A-lien
├── commands/
│   ├── __init__.py
│   ├── _helpers.py         # Shared helpers (get_provider_or_exit, confirm_action)
│   ├── email.py            # resumu, respondi, agu
│   ├── knowledge.py        # generi (text generation)
│   ├── enhancement.py      # plibonigi (text enhancement)
│   └── translation.py      # traduki (text translation)
└── data/
    ├── __init__.py
    ├── storage.py          # SQLite for agent metadata + history + styloj
    └── provider_config.py  # Provider metadata storage (non-secret config, prioritato)
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

### Provider Reference Format

All commands accepting `--provizanto` support three formats:

| Format | Example | Behavior |
|--------|---------|----------|
| None (omitted) | — | Falls back to prioritato order (see below) |
| Provider name | `--provizanto openai` | Uses that provider type directly |
| Provider:profile | `--provizanto "openai:work"` | Uses named profile key |
| Config UUID | `--provizanto a1b2c3d4-...` | Uses specific config by UUID |

Discover available UUIDs and profiles via `agento agordi ls`.

### Auto-Fallback (prioritato)

When `--provizanto` is omitted, A-agento tries configured providers in
**prioritato** order (lower `prioritato` = tried first). New providers
are auto-assigned `prioritato=0` (highest priority), shifting existing
providers by +1 — so the most recently added provider is tried first.

Ordering is visible in `agento agordi ls`:
```
Falorodo: deepseek > openai > ollama
```

Use `--prioritato/-p` on `aldoni` or `modifi` for explicit ordering:
```bash
agento agordi modifi openai --prioritato 5
```

Use `agordi default <provider>` to set a provider to `prioritato=0`.

### Sub-app Groups

- `agento agordi` — Provider configuration (default, aldoni, vidi, modifi, forigi, ls, testi)
- `agento stilo` — Writing style samples (aldoni, ls, forigi, aktiva)

### Commands

| Command | Domain | Purpose |
|---------|--------|---------|
| `generi` | General | Generate text in various formats (txt, md, json, enc) |
| `plibonigi` | General | Enhance/expand existing text (txt, md, json, enc) |
| `traduki` | General | Translate text between languages using LLM |
| `resumu` | Email | Summarize emails (requires A-lien) |
| `respondi` | Email | Draft email replies (requires A-lien) |
| `agu` | Email | Extract actions from emails (requires A-lien) |

#### Notable `generi` variants

| Invocation | Purpose |
|------------|---------|
| `generi <prompto> --formato enc` | Generate .enc knowledge entries with AI |
| `generi --formato enc --verbose` | Show LLM conversation summary |
| `generi --ligilo <URL>` | Attach web page as context |
| `generi --dosiero <path>` | Attach local file as context |

#### Notable `plibonigi` variants

| Invocation | Purpose |
|------------|---------|
| `plibonigi <INPUT> -i "make more formal"` | Enhance text with instruction |
| `<text> \| plibonigi -i "simplify"` | Stdin pipe for pipeline use |
| `plibonigi entry.enc -f enc -i "expand"` | Expand .enc entry with tool-based UUID linking |
| `plibonigi draft.md --ligilo <URL>` | Enhance with web page as reference |

### Prompt Files

All AI prompts are stored as standalone `.md` files — no embedded Python strings.
Three-tier loading:

| Tier | Location | Who edits |
|------|----------|-----------|
| User override | `~/.config/A/agento/prompts/<name>.md` | End users |
| Packaged default | `src/A_agento/prompts/<name>.md` | Prompt engineers |
| Fallback | Embedded string in `prompt_loader.py` | Developers |

To customize, copy the file you want to edit from the repo to your config:

```bash
mkdir -p ~/.config/A/agento/prompts
cp src/A_agento/prompts/generi_enc.md ~/.config/A/agento/prompts/
$EDITOR ~/.config/A/agento/prompts/generi_enc.md
```

Available prompt files:

| File | Used by | Format variables |
|------|---------|-----------------|
| `system_base` | All email commands | — |
| `system_summarize` | `resumu` | — |
| `system_reply` | `respondi` | — |
| `system_actions` | `agu` | — |
| `summarize_template` | `resumu` | `{sender}`, `{recipient}`, `{subject}`, `{body}` |
| `reply_template` | `respondi` | `{sender}`, `{subject}`, `{body}`, `{relationship}`, `{tone}` |
| `extract_actions_template` | `agu` | `{sender}`, `{subject}`, `{body}` |
| `confirm_action_template` | Action confirmation | `{action_type}`, `{action_title}`, `{action_details}` |
| `style_section_template` | Style injection | `{style_examples}` |
| `generi_txt` | `generi --formato txt` | `{title_line}`, `{context}`, `{prompto}` |
| `generi_md` | `generi --formato md` | `{title_line}`, `{context}`, `{prompto}` |
| `generi_json` | `generi --formato json` | `{title_line}`, `{context}`, `{prompto}` |
| `generi_enc` | `generi --formato enc` | `{title_line}`, `{context}`, `{prompto}` |
| `traduki` | `traduki` | `{to_target}`, `{from_source}`, `{text}` |
| `plibonigi` | `plibonigi` (txt/md/json) | `{original_text}`, `{instruction}`, `{context}`, `{formato}` |
| `plibonigi_enc` | `plibonigi --formato enc` | `{original_text}`, `{instruction}`, `{context}` |

Prompts are loaded on first use and cached in memory. Changes take effect on next A-agento invocation.

### .enc Generation Guidelines

When using `generi --formato enc`:
- Use **years only** for dates (e.g. "1879" not "1879-03-14")
- Semantic arc format: `Institucio de eduko: [ETH Zurich](#UUID, wdt:P69)` — specific entity in brackets, category label before colon
- Year entries (1879, 2024) are auto-created by `search_encik` tool when not found
- Code fences and `#` title comments are auto-stripped from LLM output

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



## Package Manager: `uv` is Required

All A-ecosystem development **must** use `uv` as the package manager:

| Operation | Command |
|-----------|---------|
| Install dependencies | `uv pip install <pkg>` |
| Install project in dev mode | `uv pip install -e .` |
| Run tests | `uv run pytest tests/` |
| Install CLI tools (poetry, etc.) | `uv tool install <tool>` |
| Add dev dependency | `uv add --dev <pkg>` |

**Exceptions:**
- `pip` in README install instructions is acceptable for end users who may not have `uv`
- Readthedocs platform build may require `pip` (platform constraint)
- Runtime `install-on-confirmation` code may fall back to `pip` if `uv` is unavailable (see A-core AGENTS.md)

## What to Avoid

- Don't auto-execute AI-suggested writes without confirmation
- Don't hardcode provider — use A.core.ai.get_provider()
- Don't duplicate A-core utilities
- Don't skip i18n (use tr_multi() / tr())
- Don't use print() — use A output functions