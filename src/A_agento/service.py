"""AgentService — orchestration for AI-powered email assistance.

Coordinates between LLM providers and A modules (email, calendar, todos, knowledge).

Usage:
    from A_agento.service import get_agent_service
    
    agent = get_agent_service()
    summaries = agent.summarize_emails(provider, unread_only=True)
    reply = agent.generate_reply(provider, email_uuid, tone="courteous")
    actions = agent.extract_actions(provider, email_uuid)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from A import info, error, tr, tr_multi

# Cross-module imports with runtime detection
_a_lien = None
_organizi_service = None
_encik_service = None


def _get_lien_service():
    """Get RetpostoService from A-lien if available."""
    global _a_lien
    if _a_lien is None:
        try:
            from A_lien.service import get_retposto_service

            _a_lien = get_retposto_service()
        except ImportError:
            pass
    return _a_lien


def _get_calendar_service():
    """Get EventService from A-organizi if available."""
    global _organizi_service
    if _organizi_service is None:
        try:
            from A_organizi.service import get_kalendaro_service

            _organizi_service = get_kalendaro_service()
        except ImportError:
            pass
    return _organizi_service


def _get_todo_service():
    """Get TodoService from A-organizi if available."""
    from A_organizi.service import get_todo_service

    return get_todo_service()


def _get_encik_service():
    """Get EncikService from A-encik if available."""
    global _encik_service
    if _encik_service is None:
        try:
            from A_encik.service import get_encik_service

            _encik_service = get_encik_service()
        except ImportError:
            pass
    return _encik_service


@dataclass
class EmailSummary:
    """Summarized email."""

    uuid: str
    sender: str
    recipients: str
    subject: str
    body: str
    summary: str
    received_at: str


@dataclass
class ActionSuggestion:
    """Extracted action from email."""

    action_type: str  # "calendar", "todo", "knowledge"
    title: str
    details: str
    metadata: dict[str, Any]


class AgentService:
    """Orchestration service for AI-powered email assistance.

    Coordinates between LLM providers and A modules:
    - A-core.ai (LLM generation)
    - A-lien (email access)
    - A-organizi (calendar, todos)
    - A-encik (knowledge)
    """

    def __init__(self):
        """Initialize agent service."""
        self._email_service = None

    @property
    def email_service(self):
        """Get email service (lazy load from A-lien)."""
        if self._email_service is None:
            self._email_service = _get_lien_service()
        if self._email_service is None:
            raise RuntimeError(
                tr_multi(
                    "A-lien ne estas instalita.",  # eo
                    "A-lien is not installed.",  # en
                    "A-lien n'est pas installé.",  # fr
                )
            )
        return self._email_service

    # --- Email fetching ---

    def get_email(self, uuid: str) -> dict[str, Any] | None:
        """Get an email by UUID.

        Args:
            uuid: Email UUID

        Returns:
            Email dict or None
        """
        from A_lien.data.storage import get_db

        db = get_db()
        return db.execute_one(
            "SELECT * FROM mesagxoj WHERE uuid = ?", (uuid,)
        )

    def list_recent_emails(
        self,
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """List recent emails.

        Args:
            limit: Max emails
            unread_only: Only unread

        Returns:
            List of email dicts
        """
        from A_lien.data.storage import get_db

        db = get_db()
        sql = "SELECT * FROM mesagxoj"
        params = []

        if unread_only:
            sql += " WHERE legita = 0"

        sql += " ORDER BY ricevita_je DESC LIMIT ?"
        params.append(limit)

        return db.execute(sql, params)

    # --- Summarization ---

    def summarize_emails(
        self,
        provider,  # LLMProvider
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[EmailSummary]:
        """Summarize recent emails.

        Args:
            provider: LLMProvider instance
            limit: Max emails
            unread_only: Only unread

        Returns:
            List of EmailSummary
        """
        from A_agento.prompts import summarize_email

        emails = self.list_recent_emails(limit=limit, unread_only=unread_only)
        if not emails:
            info(tr("Neniuj ne-legitaj retpoŝtoj."))  # No unread emails
            return []

        summaries = []
        for email in emails:
            # Parse recipients
            al = json.loads(email.get("al", "[]"))
            al_str = ", ".join(al) if al else ""

            # Build prompt
            prompt = summarize_email(
                sender=email.get("de", ""),
                recipient=al_str,
                subject=email.get("subjekto", ""),
                body=email.get("korpo", ""),
            )

            # Generate summary
            summary = provider.generate(prompt)

            summaries.append(
                EmailSummary(
                    uuid=email.get("uuid", ""),
                    sender=email.get("de", ""),
                    recipients=al_str,
                    subject=email.get("subjekto", ""),
                    body=email.get("korpo", ""),
                    summary=summary,
                    received_at=email.get("ricevita_je", ""),
                )
            )

        return summaries

    # --- Reply generation ---

    def generate_reply(
        self,
        provider,  # LLMProvider
        email_uuid: str,
        tone: str = "courteous",
        relationship: str = "professional",
    ) -> str | None:
        """Generate a smart reply draft for an email.

        Args:
            provider: LLMProvider instance
            email_uuid: Email UUID to reply to
            tone: Reply tone (courteous/casual/formal)
            relationship: Relationship context

        Returns:
            Generated reply draft or None
        """
        from A_agento.prompts import generate_reply

        email = self.get_email(email_uuid)
        if not email:
            error(tr("Retpoŝto ne trovita."))  # Email not found
            return None

        # Build prompt
        prompt = generate_reply(
            sender=email.get("de", ""),
            subject=email.get("subjekto", ""),
            body=email.get("korpo", ""),
            tone=tone,
            relationship=relationship,
        )

        # Generate reply
        return provider.generate(prompt)

    # --- Action extraction ---

    def extract_actions(
        self,
        provider,  # LLMProvider
        email_uuid: str,
    ) -> list[ActionSuggestion]:
        """Extract actionable items from an email.

        Args:
            provider: LLMProvider instance
            email_uuid: Email UUID

        Returns:
            List of ActionSuggestion
        """
        from A_agento.prompts import extract_actions

        email = self.get_email(email_uuid)
        if not email:
            error(tr("Retpoŝto ne trovita."))  # Email not found
            return []

        # Build prompt
        prompt = extract_actions(
            sender=email.get("de", ""),
            subject=email.get("subjekto", ""),
            body=email.get("korpo", ""),
        )

        # Generate JSON response
        response = provider.generate(prompt)

        # Parse JSON
        try:
            actions = json.loads(response)
        except json.JSONDecodeError:
            info(tr("Nepovis analizi la retpoŝton."))  # Could not parse email
            return []

        suggestions = []

        # Calendar
        if cal := actions.get("calendar"):
            suggestions.append(
                ActionSuggestion(
                    action_type="calendar",
                    title=cal.get("title", ""),
                    details=f"{cal.get('start', '')} - {cal.get('end', '')}",
                    metadata=cal,
                )
            )

        # Todo
        if todo := actions.get("todo"):
            suggestions.append(
                ActionSuggestion(
                    action_type="todo",
                    title=todo.get("title", ""),
                    details=f"Due: {todo.get('due', 'n/a')}",
                    metadata=todo,
                )
            )

        # Knowledge
        if knowledge := actions.get("knowledge"):
            suggestions.append(
                ActionSuggestion(
                    action_type="knowledge",
                    title=knowledge.get("title", ""),
                    details=knowledge.get("content", "")[:100],
                    metadata=knowledge,
                )
            )

        return suggestions

    # --- Action execution (with confirmation) ---

    def create_calendar_event(self, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Create calendar event (requires external confirmation).

        Args:
            metadata: Event metadata from action extraction

        Returns:
            Created event dict or None
        """
        cal_service = _get_calendar_service()
        if cal_service is None:
            info(tr("A-organizi ne estas instalita."))  # A-organizi not installed
            return None

        event_data = {
            "titolo": metadata.get("title", ""),
            "komenco": metadata.get("start", ""),
            "fino": metadata.get("end", ""),
            "priskribo": metadata.get("description", ""),
        }
        return cal_service.create(event_data)

    def create_todo(self, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Create todo (requires external confirmation).

        Args:
            metadata: Todo metadata from action extraction

        Returns:
            Created todo dict or None
        """
        try:
            todo_service = _get_todo_service()
        except Exception:
            info(tr("A-organizi ne estas instalita."))  # A-organizi not installed
            return None

        todo_data = {
            "titolo": metadata.get("title", ""),
            "prioritato": metadata.get("priority", "normal"),
            "deveno": metadata.get("due", ""),
        }
        return todo_service.create(todo_data)

    def create_knowledge_entry(
        self, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create knowledge entry (requires external confirmation).

        Args:
            metadata: Knowledge metadata from action extraction

        Returns:
            Created entry dict or None
        """
        encik_service = _get_encik_service()
        if encik_service is None:
            info(tr("A-encik ne estas instalita."))  # A-encik not installed
            return None

        entry_data = {
            "titolo": metadata.get("title", ""),
            "enhavo": metadata.get("content", ""),
        }
        return encik_service.create(entry_data)


# Singleton
_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    """Get the singleton AgentService.

    Returns:
        AgentService instance
    """
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service


__all__ = [
    "AgentService",
    "EmailSummary",
    "ActionSuggestion",
    "get_agent_service",
]