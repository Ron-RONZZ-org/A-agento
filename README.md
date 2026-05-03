# A-agento — AI Email Agent

A-agento provides AI-powered email assistance for the A ecosystem, leveraging LLM providers for summarization, smart reply generation, and action extraction from emails.

## Features

- **Email Summarization**: Summarize recent emails using LLM
- **Smart Reply**: Generate draft replies with context awareness
- **Action Extraction**: Parse emails to suggest calendar events, todos, knowledge entries

## Installation

```bash
cd A-agento
pip install -e .
```

## Quick Start

### 1. Configure LLM Provider

**Option A: Ollama (local, privacy-first)**
```bash
# Install and start Ollama
ollama pull llama2
```

**Option B: OpenAI (cloud)**
```bash
python -c "from A.core.ai import save_api_key; save_api_key('your-openai-key')"
```

### 2. Set Default Provider
```bash
python -c "from A.core.ai import set_default_provider; set_default_provider('ollama')"
```

### 3. Run Commands

```bash
# Summarize recent emails
agento resumu

# Generate smart reply draft
agento respondu --uuid <email-uuid>

# Extract actions from email
agento agu --uuid <email-uuid>
```

## Commands

| Command | Description |
|---------|-------------|
| `resumu` | Summarize recent unread emails |
| `respondu` | Generate smart reply draft |
| `agu` | Extract actions (calendar, todo, encik) |

## Security

- API keys stored in system keyring (never SQLite)
- All AI-suggested writes require user confirmation
- Privacy: Ollama runs fully local

## Architecture

A-agento coordinates between:
- A-core.ai (LLM providers)
- A-lien (email access)
- A-organizi (calendar, todos)
- A-encik (knowledge base)

All cross-module imports use runtime detection.

## Requirements

- Python 3.11+
- A-core
- typer + rich

## License

GPL-3.0-only