# A-agento — General LLM Interface

A-agento provides the general LLM interface for the A ecosystem — text generation, translation, and AI-powered email assistance.

## Features

- **Text Translation**: Translate text between languages via LLM
- **Text Generation**: Generate content in txt, md, json, and .enc formats
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
Ollama needs no API key; for cloud providers, add your key first:
```bash
agento agordi aldoni openai --key sk-...
```
Then set as default (highest priority, tried first in auto-fallback):
```bash
agento agordi default ollama
```

### 3. Run Commands

```bash
# Translate text
agento traduki "Hello world" -c fr
agento traduki doc.txt -c eo -K tradukita.md

# Generate content
agento generi "quantum computing" --formato md

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
| `traduki` | Translate text between languages |
| `generi` | Generate content with AI (txt, md, json, enc) |
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
