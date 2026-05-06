"""Prompt templates for A-agento.

Provides reusable prompt templates for different tasks.
All prompts support file-based override via ~/.config/A/agento/prompts/.
See prompt_loader.py for details.
"""

from __future__ import annotations

from A_agento.prompt_loader import load_prompt


# ============== SYSTEM PROMPTS ==============
# Embedded defaults — overridden by files in ~/.config/A/agento/prompts/ if present.

SYSTEM_BASE_DEFAULT = """You are an email assistant.
- Always respond in the language of the user's request
- Keep responses concise and actionable
- Never make up information not present in the email
- Use ISO 8601 format for all dates (YYYY-MM-DD or YYYY-MM-DDTHH:MMZ)"""

SYSTEM_SUMMARIZE_DEFAULT = f"""{SYSTEM_BASE_DEFAULT}

When summarizing emails:
- Extract the key point in 2-3 sentences
- Focus on what the sender wants or what's being communicated
- Note any deadlines or action items mentioned"""

SYSTEM_REPLY_DEFAULT = f"""{SYSTEM_BASE_DEFAULT}

When generating replies:
- Match the tone and formality of the original email
- Address all questions or requests in the original
- Keep it concise (2-4 sentences)
- Include appropriate greeting and sign-off"""

SYSTEM_ACTIONS_DEFAULT = f"""{SYSTEM_BASE_DEFAULT}

When extracting actions from emails:
- Return ONLY valid JSON, no extra text
- Use ISO 8601 format for all dates (YYYY-MM-DDTHH:MMZ)
- Return null for fields with no data
- Only extract actions explicitly mentioned, never infer
- Extract location (physical address or meeting link) if mentioned
- Extract recurrence pattern (FREQ=WEEKLY;BYDAY=MO) if mentioned
- Extract reminder offset (15m, 1h, 1d) if mentioned
- For knowledge entries, look for vt# or ec# references to existing entries"""


def _get_system_base() -> str:
    """Get system base prompt (user-overridable)."""
    return load_prompt("system_base", SYSTEM_BASE_DEFAULT)


def _get_system_summarize() -> str:
    """Get summarization system prompt (composed from base if not overridden)."""
    return load_prompt("system_summarize", SYSTEM_SUMMARIZE_DEFAULT)


def _get_system_reply() -> str:
    """Get reply system prompt."""
    return load_prompt("system_reply", SYSTEM_REPLY_DEFAULT)


def _get_system_actions() -> str:
    """Get actions system prompt."""
    return load_prompt("system_actions", SYSTEM_ACTIONS_DEFAULT)


# ============== TEMPLATE PROMPTS ==============

SUMMARIZE_TEMPLATE_DEFAULT = """Summarize the following email in 2-3 sentences:

From: {sender}
To: {recipient}
Subject: {subject}

Body:
{body}

Summary:"""

REPLY_TEMPLATE_DEFAULT = """Generate a professional email reply draft.

Context:
- Original email from: {sender}
- Subject: {subject}
- Original body: {body}

Your relationship: {relationship}
Tone: {tone}

Generate a concise reply draft (2-4 sentences):"""

EXTRACT_ACTIONS_TEMPLATE_DEFAULT = """Analyze this email and extract any actionable items.

Email:
From: {sender}
Subject: {subject}
Body: {body}

Extract:
1. Any dates/times mentioned → calendar event (include location if found)
2. Any tasks/delegate requests → todo
3. Any new information → knowledge entry

Respond in this JSON format:
{{
    "calendar": {{"title": "", "start": "", "end": "", "description": "", "location": "", "ripeto": "", "remind": ""}} or null,
    "todo": {{"title": "", "due": "", "priority": ""}} or null,
    "knowledge": {{"title": "", "content": "", "ligilo": [], "superklaso": []}} or null
}}

If nothing actionable, respond with null for all three fields.

Notes:
- ripeto format: FREQ=DAILY, FREQ=WEEKLY;BYDAY=MO,WE,FR, FREQ=MONTHLY
- remind format: 15m, 1h, 1d (offset before event)
- location: physical address or meeting link (Zoom, Meet, etc.)
- knowledge.ligilo: list of UUIDs or vt#/ec# references to link to
- knowledge.superklaso: list of parent category UUIDs"""

CONFIRM_ACTION_TEMPLATE_DEFAULT = """The AI has suggested the following action:

{action_type}: {action_title}
Details: {action_details}

Do you want to proceed? [(y)es/(n)o]"""

STYLE_SECTION_TEMPLATE_DEFAULT = """
<writing-style>
The user's writing style, based on their past emails:
<examples>
{style_examples}
</examples>
When generating content, mirror the above style in terms of:
- Sentence length and complexity
- Formality level
- Use of bullets vs prose
- Greeting/sign-off patterns
- Punctuation and capitalization style
</writing-style>

"""


def _get_template(name: str, default: str) -> str:
    """Load a template prompt with file override support.
    
    Args:
        name: Prompt file name
        default: Embedded default string
    Returns:
        Prompt string
    """
    return load_prompt(name, default)


# ============== PUBLIC FUNCTIONS ==============


def summarize_email(
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> str:
    """Format email summarization prompt."""
    system = _get_system_summarize()
    template = _get_template("summarize_template", SUMMARIZE_TEMPLATE_DEFAULT)
    return f"{system}\n\n" + template.format(
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=body[:2000],
    )


def generate_reply(
    sender: str,
    subject: str,
    body: str,
    relationship: str = "professional",
    tone: str = "courteous",
) -> str:
    """Format smart reply generation prompt."""
    system = _get_system_reply()
    template = _get_template("reply_template", REPLY_TEMPLATE_DEFAULT)
    return f"{system}\n\n" + template.format(
        sender=sender,
        subject=subject,
        body=body[:1500],
        relationship=relationship,
        tone=tone,
    )


def extract_actions(
    sender: str,
    subject: str,
    body: str,
) -> str:
    """Format action extraction prompt."""
    system = _get_system_actions()
    template = _get_template("extract_actions_template", EXTRACT_ACTIONS_TEMPLATE_DEFAULT)
    return f"{system}\n\n" + template.format(
        sender=sender,
        subject=subject,
        body=body[:2000],
    )


def format_confirm(
    action_type: str,
    action_title: str,
    action_details: str,
) -> str:
    """Format action confirmation prompt."""
    template = _get_template("confirm_action_template", CONFIRM_ACTION_TEMPLATE_DEFAULT)
    return template.format(
        action_type=action_type,
        action_title=action_title,
        action_details=action_details,
    )


def inject_style(prompt: str, style_samples: list[str]) -> str:
    """Inject style examples into prompt with structured XML delimiters."""
    if not style_samples:
        return prompt
    examples = "\n\n".join(
        f"<sample>{s}</sample>" for s in style_samples[:3]
    )
    template = _get_template("style_section_template", STYLE_SECTION_TEMPLATE_DEFAULT)
    style_section = template.format(style_examples=examples)
    return style_section + "\n\n" + prompt


__all__ = [
    "summarize_email",
    "generate_reply",
    "extract_actions",
    "format_confirm",
    "inject_style",
]
