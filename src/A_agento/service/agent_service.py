"""AgentService — orchestration for AI-powered email assistance.

Base class with email fetching methods. AI summarization and action
execution are provided by mixins in separate modules.
"""

from __future__ import annotations

from typing import Any

from A import info, warning, error, tr, tr_multi

from A_agento.contract import validate_email_dict
from A_agento.service.registry import get_lien_service
from A_agento.service.summarization_mixin import SummarizationMixin
from A_agento.service.action_mixin import ActionMixin


class AgentService(SummarizationMixin, ActionMixin):
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
            self._email_service = get_lien_service()
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
        """Get an email by UUID (full or short prefix) via A-lien service.

        Tries exact match first, then prefix fallback (LIKE 'prefix%').

        Args:
            uuid: Email UUID or unique prefix

        Returns:
            Email dict or None if not found / ambiguous
        """
        lien = get_lien_service()
        if lien is None:
            return self._get_email_direct(uuid)

        # Try to use service API first — exact match
        try:
            email = lien.get(uuid)
        except (AttributeError, TypeError):
            return self._get_email_direct(uuid)

        if email:
            # Validate against contract
            is_valid, missing = validate_email_dict(email)
            if not is_valid:
                warning(tr_multi(
                    f"A-lien email mankas: {', '.join(missing)}",
                    f"A-lien email missing: {', '.join(missing)}",
                    f"Email A-lien manquant : {', '.join(missing)}",
                ))
            return email

        # Prefix fallback — try find_message_by_uuid_prefix
        try:
            matches = lien.find_message_by_uuid_prefix(uuid)
        except (AttributeError, TypeError):
            return self._get_email_direct(uuid)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            warning(tr_multi(
                f"Pluraj mesaĝoj kongruas kun '{uuid}'.",
                f"Multiple messages match '{uuid}'.",
                f"Plusieurs messages correspondent à '{uuid}'.",
            ))
            return None

        return self._get_email_direct(uuid)

    def _get_email_direct(self, uuid: str) -> dict[str, Any] | None:
        """Fallback: direct DB access when service API unavailable.

        Tries exact match first, then prefix fallback.
        """
        try:
            from A_lien.data.storage import get_db

            db = get_db()
            # Exact match
            email = db.execute_one(
                "SELECT * FROM mesagoj WHERE uuid = ?", (uuid,)
            )
            if email:
                return email
            # Prefix fallback
            rows = db.execute(
                "SELECT * FROM mesagoj WHERE uuid LIKE ?", (f"{uuid}%",)
            )
            if len(rows) == 1:
                return rows[0]
            return None
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
            result = db.execute_one("SELECT COUNT(*) as count FROM mesagoj")
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
        lien = get_lien_service()
        if lien is None:
            return self._list_recent_emails_direct(limit, unread_only)

        try:
            emails = lien.list_recent(limit=limit)
        except (AttributeError, TypeError):
            return self._list_recent_emails_direct(limit, unread_only)

        if emails:
            is_valid, missing = validate_email_dict(emails[0])
            if not is_valid:
                warning(tr_multi(
                    f"A-lien emails mankas: {', '.join(missing)}",
                    f"A-lien emails missing: {', '.join(missing)}",
                    f"Emails A-lien manquants : {', '.join(missing)}",
                ))

        return emails

    def _list_recent_emails_direct(
        self,
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Fallback: direct DB access when service API unavailable."""
        try:
            from A_lien.data.storage import get_db

            db = get_db()
            sql = "SELECT * FROM mesagoj"
            params: list[Any] = []

            if unread_only:
                sql += " WHERE legita = 0"

            sql += " ORDER BY ricevita_je DESC LIMIT ?"
            params.append(limit)

            return db.execute(sql, params)
        except ImportError:
            return []


__all__ = [
    "AgentService",
]
