"""Prompt templates for A-agento.

Provides reusable prompt templates for different tasks:
- Email summarization
- Smart reply generation
- Action extraction (calendar, todo, encik)
- Style injection for personalized output
"""

from __future__ import annotations

from typing import Any


# Style injection template
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
1. Any dates/times mentioned → calendar event
2. Any tasks/delegate requests → todo
3. Any new information → knowledge entry

Respond in this JSON format:
{{
    "calendar": {{"title": "", "start": "", "end": "", "description": ""}} or null,
    "todo": {{"title": "", "due": "", "priority": ""}} or null,
    "knowledge": {{"title": "", "content": ""}} or null
}}

If nothing actionable, respond with null for all three fields."""

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
        Formatted prompt
    """
    return SUMMARIZE_TEMPLATE.format(
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
        Formatted prompt
    """
    return REPLY_TEMPLATE.format(
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
        Formatted prompt
    """
    return EXTRACT_ACTIONS_TEMPLATE.format(
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