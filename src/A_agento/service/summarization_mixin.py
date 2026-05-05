"""SummarizationMixin — AI summarization, reply generation, and action extraction.

Mixed into AgentService to provide LLM-powered email processing.
"""

from __future__ import annotations

import json
from typing import Any

from A import info, error, tr, tr_multi

from A_agento.service.helpers import EmailSummary, ActionSuggestion, _extract_json
from A_agento.service.registry import get_lien_service


class SummarizationMixin:
    """Mixin providing AI summarization and action extraction methods."""

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
        lien = get_lien_service()
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
            al = json.loads(email.get("al", "[]"))
            al_str = ", ".join(al) if al else ""

            prompt = summarize_email(
                sender=email.get("de", ""),
                recipient=al_str,
                subject=email.get("subjekto", ""),
                body=email.get("korpo", ""),
            )

            # Inject style samples if available
            from A_agento.prompts import inject_style
            from A_agento.data.storage import search_similar_samples

            email_content = (
                f"{email.get('subjekto', '')} {email.get('korpo', '')}"
            )
            similar = search_similar_samples(
                email_content, sample_type="summary", limit=2
            )
            if similar:
                style_samples = [s["content"] for s in similar]
                prompt = inject_style(prompt, style_samples)

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
        from A_agento.data.storage import search_similar_samples

        email = self.get_email(email_uuid)
        if not email:
            error(
                tr_multi(
                    "Retposxto ne trovita.",
                    "Email not found.",
                    "Email non trouve.",
                )
            )
            return None

        prompt = generate_reply(
            sender=email.get("de", ""),
            subject=email.get("subjekto", ""),
            body=email.get("korpo", ""),
            tone=tone,
            relationship=relationship,
        )

        email_content = (
            f"{email.get('subjekto', '')} {email.get('korpo', '')}"
        )
        similar = search_similar_samples(
            email_content, sample_type="reply", limit=3
        )
        if similar:
            style_samples = [s["content"] for s in similar]
            prompt = inject_style(prompt, style_samples)

        return provider.generate(prompt)

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
            error(
                tr_multi(
                    "Retposxto ne trovita.",
                    "Email not found.",
                    "Email non trouve.",
                )
            )
            return []

        prompt = extract_actions(
            sender=email.get("de", ""),
            subject=email.get("subjekto", ""),
            body=email.get("korpo", ""),
        )

        response = provider.generate(prompt)
        actions = _extract_json(response)
        if not actions:
            info(
                tr_multi(
                    "Nepovis analizi la retposton.",
                    "Could not parse the email.",
                    "Impossible d'analyser l'email.",
                )
            )
            return []

        suggestions: list[ActionSuggestion] = []

        if cal := actions.get("calendar"):
            suggestions.append(
                ActionSuggestion(
                    action_type="calendar",
                    title=cal.get("title", ""),
                    details=f"{cal.get('start', '')} - {cal.get('end', '')}",
                    metadata=cal,
                )
            )

        if todo := actions.get("todo"):
            suggestions.append(
                ActionSuggestion(
                    action_type="todo",
                    title=todo.get("title", ""),
                    details=f"Due: {todo.get('due', 'n/a')}",
                    metadata=todo,
                )
            )

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


__all__ = [
    "SummarizationMixin",
]
