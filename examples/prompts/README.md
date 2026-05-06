# A-agento Custom Prompt Files

Copy any `.prompt.example` file to `~/.config/A/agento/prompts/<name>.prompt` to override the embedded default.

```bash
# Copy all examples
mkdir -p ~/.config/A/agento/prompts
cp examples/prompts/*.prompt.example ~/.config/A/agento/prompts/

# Rename to remove .example suffix
for f in ~/.config/A/agento/prompts/*.example; do
  mv "$f" "${f%.example}"
done

# Edit any prompt
$EDITOR ~/.config/A/agento/prompts/system_base.prompt
```

Prompts are loaded on first use and cached in memory. Changes take effect on next A-agento invocation.

## Available prompts

| File | Command | Format variables |
|------|---------|-----------------|
| `system_base` | All email commands | — |
| `system_summarize` | `resumu` | — |
| `summarize_template` | `resumu` | `{sender}`, `{recipient}`, `{subject}`, `{body}` |
| `generi_enc` | `generi --formato enc` | `{title_line}`, `{prompto}` |
| ... (see AGENTS.md for full list) | | |

## Notes

- Keep the `{variable}` placeholders intact — they're filled at runtime
- Overly long prompts increase token usage and latency
- Invalid prompt files fall back to embedded defaults
