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


# --- JSON extraction helper ---


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response (handles markdown fences, leading text).

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    import re

    # Try to find ```json ... ``` block first
    if match := re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL):
        text = match.group(1)

    # Remove any leading/trailing non-JSON text
    text = text.strip()

    # Try direct parse
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Last resort: find first { and last }
    if (start := text.find("{")) != -1 and (end := text.rfind("}")) != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


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
    global _organizi_service
    if _organizi_service is None:
        try:
            from A_organizi.service import get_todo_service

            _organizi_service = get_todo_service()
        except ImportError:
            pass
    return _organizi_service


def _get_encik_service():
    """Get EncikService from A-encik if available."""
    global _encik_service
    if _encik_service is None:
        try:
            from A_encik.service import get_service

            _encik_service = get_service()
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
        """Get an email by UUID via A-lien service.

        Args:
            uuid: Email UUID

        Returns:
            Email dict or None
        """
        lien = _get_lien_service()
        if lien is None:
            # Fallback to direct DB access
            return self._get_email_direct(uuid)

        # Try to use service API first
        try:
            return lien.get(uuid)
        except (AttributeError, TypeError):
            # Service doesn't have get() method, use fallback
            return self._get_email_direct(uuid)

    def _get_email_direct(self, uuid: str) -> dict[str, Any] | None:
        """Fallback: direct DB access when service API unavailable."""
        try:
            from A_lien.data.storage import get_db

            db = get_db()
            return db.execute_one(
                "SELECT * FROM mesagxoj WHERE uuid = ?", (uuid,)
            )
        except ImportError:
            return None

    def _check_email_accounts(self) -> bool:
        """Check if any email accounts are configured.

        Returns:
            True if accounts exist, False otherwise
        """
        try:
            from A_lien.data.storage import get_db

            db = get_db()
            accounts = db.execute_one("SELECT COUNT(*) as count FROM kontoj")
            return accounts and accounts.get("count", 0) > 0
        except ImportError:
            return False

    def _check_emails_exist(self) -> bool:
        """Check if any emails exist in the database.

        Returns:
            True if emails exist, False otherwise
        """
        try:
            from A_lien.data.storage import get_db

            db = get_db()
            result = db.execute_one("SELECT COUNT(*) as count FROM mesagxoj")
            return result and result.get("count", 0) > 0
        except ImportError:
            return False

    def list_recent_emails(
        self,
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """List recent emails via A-lien service.

        Args:
            limit: Max emails
            unread_only: Only unread

        Returns:
            List of email dicts
        """
        lien = _get_lien_service()
        if lien is None:
            # Fallback to direct DB access
            return self._list_recent_emails_direct(limit, unread_only)

        # Try to use service API first
        try:
            # Try list_recent method
            return lien.list_recent(limit=limit)
        except (AttributeError, TypeError):
            # Fallback to direct DB
            return self._list_recent_emails_direct(limit, unread_only)

    def _list_recent_emails_direct(
        self,
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Fallback: direct DB access when service API unavailable."""
        try:
            from A_lien.data.storage import get_db

            db = get_db()
            sql = "SELECT * FROM mesagxoj"
            params = []

            if unread_only:
                sql += " WHERE legita = 0"

            sql += " ORDER BY ricevita_je DESC LIMIT ?"
            params.append(limit)

            return db.execute(sql, params)
        except ImportError:
            return []

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

        # Check if A-lien is installed
        lien = _get_lien_service()
        if lien is None and not self._check_email_accounts():
            info(
                tr_multi(
                    "Neniu retpoŝta konto estas agordita. Uzu 'A lien retposto aldoni-konton'.",  # eo
                    "No email accounts configured. Use 'A lien retposto aldoni-konton'.",  # en
                    "Aucun compte email configuré. Utilisez 'A lien retposto aldoni-konton'.",  # fr
                )
            )
            return []

        emails = self.list_recent_emails(limit=limit, unread_only=unread_only)
        if not emails:
            if unread_only:
                info(
                    tr_multi(
                        "Neniuj ne-legitaj retpoŝtoj.",  # eo
                        "No unread emails.",  # en
                        "Aucun email non lu.",  # fr
                    )
                )
            else:
                info(
                    tr_multi(
                        "Neniuj retpoŝtoj. Provu synkronigi kun 'A lien retposto preni'.",  # eo
                        "No emails. Try syncing with 'A lien retposto preni'.",  # en
                        "Aucun email. Essayez de synchroniser avec 'A lien retposto preni'.",  # fr
                    )
                )
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

            # Inject style samples if available
            from A_agento.prompts import inject_style
            from A_agento.data.storage import search_similar_samples
            email_content = f"{email.get('subjekto', '')} {email.get('korpo', '')}"
            similar = search_similar_samples(email_content, sample_type="summary", limit=2)
            if similar:
                style_samples = [s["content"] for s in similar]
                prompt = inject_style(prompt, style_samples)

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
        from A_agento.prompts import generate_reply, inject_style
        from A_agento.data.storage import get_active_samples_by_type, search_similar_samples

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

        # Inject style samples if available
        email_content = f"{email.get('subjekto', '')} {email.get('korpo', '')}"
        similar = search_similar_samples(email_content, sample_type="reply", limit=3)
        if similar:
            style_samples = [s["content"] for s in similar]
            prompt = inject_style(prompt, style_samples)

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

        # Parse JSON with robust extraction
        actions = _extract_json(response)
        if not actions:
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