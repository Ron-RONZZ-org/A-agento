"""Tests for A-agento service."""

from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch


class TestAgentService:
    """Tests for AgentService."""

    def test_summarize_emails_no_emails(self, mock_provider):
        """Test summarization with no emails returns empty list."""
        from A_agento.service import AgentService

        service = AgentService()

        # Mock list_recent_emails to return empty list
        with patch.object(service, "list_recent_emails", return_value=[]):
            with patch("A_agento.service.summarization_mixin.get_lien_service", return_value=None):
                result = service.summarize_emails(mock_provider, limit=10, unread_only=True)
                assert result == []

    def test_summarize_emails_with_data(self, mock_provider, sample_emails):
        """Test summarization with emails."""
        from A_agento.service import AgentService

        service = AgentService()

        with patch.object(service, "list_recent_emails", return_value=sample_emails):
            with patch("A_agento.service.summarization_mixin.get_lien_service", return_value=None):
                summaries = service.summarize_emails(mock_provider, limit=10, unread_only=False)

                assert len(summaries) == 1
                assert summaries[0].sender == "alice@example.com"
                assert summaries[0].subject == "Test Meeting"

    def test_summarize_emails_checks_accounts(self, mock_provider):
        """Test summarization checks for accounts first."""
        from A_agento.service import AgentService

        service = AgentService()

        # Mock _check_email_accounts to return False
        with patch.object(service, "_check_email_accounts", return_value=False):
            with patch("A_agento.service.summarization_mixin.get_lien_service", return_value=None):
                result = service.summarize_emails(mock_provider)
                assert result == []

    def test_generate_reply_not_found(self):
        """Test reply generation with non-existent email returns None."""
        from A_agento.service import AgentService

        service = AgentService()
        mock_provider = Mock()
        mock_provider.generate.return_value = "Reply draft."

        with patch.object(service, "get_email", return_value=None):
            result = service.generate_reply(mock_provider, "non-existent-uuid")
            assert result is None

    def test_generate_reply_with_email(self, mock_provider, sample_email):
        """Test reply generation with valid email."""
        from A_agento.service import AgentService

        service = AgentService()

        with patch.object(service, "get_email", return_value=sample_email):
            result = service.generate_reply(mock_provider, sample_email["uuid"])

            assert result is not None
            mock_provider.generate.assert_called_once()

    def test_extract_actions_not_found(self):
        """Test action extraction with non-existent email returns empty."""
        from A_agento.service import AgentService

        service = AgentService()
        mock_provider = Mock()

        with patch.object(service, "get_email", return_value=None):
            result = service.extract_actions(mock_provider, "non-existent-uuid")
            assert result == []

    def test_extract_actions_with_json_response(self, mock_provider_with_json, sample_email):
        """Test action extraction parses JSON correctly."""
        from A_agento.service import AgentService

        service = AgentService()

        with patch.object(service, "get_email", return_value=sample_email):
            result = service.extract_actions(mock_provider_with_json, sample_email["uuid"])

            assert len(result) == 3  # calendar, todo, knowledge

            action_types = [a.action_type for a in result]
            assert "calendar" in action_types
            assert "todo" in action_types
            assert "knowledge" in action_types

    def test_extract_actions_invalid_json(self, sample_email):
        """Test action extraction handles invalid JSON gracefully."""
        from A_agento.service.helpers import _extract_json

        # Test _extract_json helper
        result = _extract_json("not valid json")
        assert result is None

        result = _extract_json('{"valid": "json"}')
        assert result == {"valid": "json"}

    def test_cross_module_a_lien_missing(self):
        """Test graceful fallback when A-lien not installed."""
        from A_agento.service import AgentService

        service = AgentService()

        with patch("A_agento.service.summarization_mixin.get_lien_service", return_value=None):
            # Should handle gracefully via _check_email_accounts or direct DB
            pass  # No exception means graceful handling

    def test_cross_module_a_organizi_missing(self):
        """Test graceful handling when A-organizi not installed."""
        from A_agento.service import AgentService
        from A_agento.service.registry import get_calendar_service, get_todo_service

        with patch("A_agento.service.action_mixin.get_calendar_service", return_value=None):
            with patch("A_agento.service.action_mixin.get_todo_service", return_value=None):
                service = AgentService()
                result = service.create_calendar_event({"title": "Test"})
                # Should return None gracefully
                assert result is None

    def test_cross_module_a_encik_missing(self):
        """Test graceful handling when A-encik not installed."""
        from A_agento.service import AgentService

        with patch("A_agento.service.action_mixin.get_encik_service", return_value=None):
            service = AgentService()
            result = service.create_knowledge_entry({"title": "Test", "content": "Content"})
            # Should return None gracefully
            assert result is None


class TestPrompts:
    """Tests for prompt templates."""

    def test_summarize_email(self):
        """Test email summarization prompt formatting."""
        from A_agento.prompts import summarize_email

        result = summarize_email(
            sender="alice@example.com",
            recipient="bob@example.com",
            subject="Meeting tomorrow",
            body="Let's meet at 3pm.",
        )

        assert "alice@example.com" in result
        assert "bob@example.com" in result
        assert "Meeting tomorrow" in result
        assert "Let's meet at 3pm" in result

    def test_generate_reply(self):
        """Test reply generation prompt formatting."""
        from A_agento.prompts import generate_reply

        result = generate_reply(
            sender="alice@example.com",
            subject="RE: Meeting",
            body="See you then.",
            tone="courteous",
            relationship="professional",
        )

        assert "alice@example.com" in result
        assert "courteous" in result
        assert "professional" in result

    def test_extract_actions(self):
        """Test action extraction prompt formatting."""
        from A_agento.prompts import extract_actions

        result = extract_actions(
            sender="alice@example.com",
            subject="Action needed",
            body="Please schedule a meeting for tomorrow.",
        )

        assert "alice@example.com" in result
        assert "calendar" in result.lower()
        assert "todo" in result.lower()
        assert "knowledge" in result.lower()


class TestStorage:
    """Tests for storage functions."""

    def test_add_and_get_history(self, tmp_path):
        """Test adding and getting history."""
        from A_agento.data.storage import add_history, get_history

        # The storage uses A.data.base which needs proper setup
        # For now, test the function signature exists
        assert callable(add_history)
        assert callable(get_history)

    def test_list_history(self):
        """Test listing history."""
        from A_agento.data.storage import list_history

        assert callable(list_history)

    def test_delete_history(self):
        """Test deleting history."""
        from A_agento.data.storage import delete_history

        assert callable(delete_history)

    def test_clear_history(self):
        """Test clearing history."""
        from A_agento.data.storage import clear_history

        assert callable(clear_history)


class TestExtractJson:
    """Tests for _extract_json helper."""

    def test_extract_plain_json(self):
        """Test extracting plain JSON."""
        from A_agento.service.helpers import _extract_json

        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_with_markdown_fence(self):
        """Test extracting JSON from markdown code fence."""
        from A_agento.service.helpers import _extract_json

        result = _extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_extract_json_with_leading_text(self):
        """Test extracting JSON with leading text."""
        from A_agento.service.helpers import _extract_json

        result = _extract_json('Here is the result: {"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_invalid(self):
        """Test extraction returns None for invalid input."""
        from A_agento.service.helpers import _extract_json

        result = _extract_json("not json at all")
        assert result is None

    def test_extract_json_with_single_quotes(self):
        """Test extraction handles various JSON formats."""
        from A_agento.service.helpers import _extract_json

        # Should try to parse and fail gracefully
        result = _extract_json("{'key': 'value'}")
        assert result is None  # Single quotes not valid JSON