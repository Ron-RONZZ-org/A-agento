"""Prompt templates for A-agento.

Provides reusable prompt templates for different tasks:
- Email summarization
- Smart reply generation
- Action extraction (calendar, todo, encik)
- Style injection for personalized output
- System prompts for consistent LLM behavior
"""

from __future__ import annotations

from typing import Any


# ============== SYSTEM PROMPTS ==============
# Global system instructions for all operations

SYSTEM_BASE = """You are an email assistant.
- Always respond in the language of the user's request
- Keep responses concise and actionable
- Never make up information not present in the email
- Use ISO 8601 format for all dates (YYYY-MM-DD or YYYY-MM-DDTHH:MMZ)"""

SYSTEM_SUMMARIZE = f"""{SYSTEM_BASE}

When summarizing emails:
- Extract the key point in 2-3 sentences
- Focus on what the sender wants or what's being communicated
- Note any deadlines or action items mentioned"""

SYSTEM_REPLY = f"""{SYSTEM_BASE}

When generating replies:
- Match the tone and formality of the original email
- Address all questions or requests in the original
- Keep it concise (2-4 sentences)
- Include appropriate greeting and sign-off"""

SYSTEM_ACTIONS = f"""{SYSTEM_BASE}

When extracting actions from emails:
- Return ONLY valid JSON, no extra text
- Use ISO 8601 format for all dates (YYYY-MM-DDTHH:MMZ)
- Return null for fields with no data
- Only extract actions explicitly mentioned, never infer
- Extract location (physical address or meeting link) if mentioned
- Extract recurrence pattern (FREQ=WEEKLY;BYDAY=MO) if mentioned
- Extract reminder offset (15m, 1h, 1d) if mentioned
- For knowledge entries, look for vt# or ec# references to existing entries"""

# ============== STYLE INJECTION ==============
STYLE_SECTION_TEMPLATE = """
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

# Email summarization prompt
SUMMARIZE_TEMPLATE = """Summarize the following email in 2-3 sentences:

From: {sender}
To: {recipient}
Subject: {subject}

Body:
{body}

Summary:"""

# Smart reply generation prompt
REPLY_TEMPLATE = """Generate a professional email reply draft.

Context:
- Original email from: {sender}
- Subject: {subject}
- Original body: {body}

Your relationship: {relationship}
Tone: {tone}

Generate a concise reply draft (2-4 sentences):"""

# Action extraction prompt
EXTRACT_ACTIONS_TEMPLATE = """Analyze this email and extract any actionable items.

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

# Action confirmation prompt
CONFIRM_ACTION_TEMPLATE = """The AI has suggested the following action:

{action_type}: {action_title}
Details: {action_details}

Do you want to proceed? [(y)es/(n)o]"""


def summarize_email(
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> str:
    """Format email summarization prompt.

    Args:
        sender: Email sender
        recipient: Email recipient
        subject: Email subject
        body: Email body

    Returns:
        Formatted prompt with system instructions
    """
    return f"{SYSTEM_SUMMARIZE}\n\n" + SUMMARIZE_TEMPLATE.format(
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=body[:2000],  # Truncate long body
    )


def generate_reply(
    sender: str,
    subject: str,
    body: str,
    relationship: str = "professional",
    tone: str = "courteous",
) -> str:
    """Format smart reply generation prompt.

    Args:
        sender: Email sender
        subject: Email subject
        body: Email body
        relationship: Relationship context (professional/personal/family)
        tone: Tone (courteous/casual/formal)

    Returns:
        Formatted prompt with system instructions
    """
    return f"{SYSTEM_REPLY}\n\n" + REPLY_TEMPLATE.format(
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
    """Format action extraction prompt.

    Args:
        sender: Email sender
        subject: Email subject
        body: Email body

    Returns:
        Formatted prompt with system instructions
    """
    return f"{SYSTEM_ACTIONS}\n\n" + EXTRACT_ACTIONS_TEMPLATE.format(
        sender=sender,
        subject=subject,
        body=body[:2000],
    )


def format_confirm(
    action_type: str,
    action_title: str,
    action_details: str,
) -> str:
    """Format action confirmation prompt.

    Args:
        action_type: Type of action (calendar/todo/knowledge)
        action_title: Title of action
        action_details: Details of action

    Returns:
        Formatted confirmation prompt
    """
    return CONFIRM_ACTION_TEMPLATE.format(
        action_type=action_type,
        action_title=action_title,
        action_details=action_details,
    )


def inject_style(prompt: str, style_samples: list[str]) -> str:
    """Inject style examples into prompt with structured XML delimiters.

    Args:
        prompt: Base prompt template
        style_samples: List of writing samples (max 3)

    Returns:
        Prompt with style injection prepended
    """
    if not style_samples:
        return prompt

    examples = "\n\n".join(
        f"<sample>{s}</sample>" for s in style_samples[:3]
    )
    style_section = STYLE_SECTION_TEMPLATE.format(
        style_examples=examples
    )
    return style_section + "\n\n" + prompt


__all__ = [
    "SUMMARIZE_TEMPLATE",
    "REPLY_TEMPLATE",
    "EXTRACT_ACTIONS_TEMPLATE",
    "CONFIRM_ACTION_TEMPLATE",
    "STYLE_SECTION_TEMPLATE",
    "summarize_email",
    "generate_reply",
    "extract_actions",
    "format_confirm",
    "inject_style",
]
    "summarize_email",
    "generate_reply",
    "extract_actions",
    "format_confirm",
]