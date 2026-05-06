"""Tests for A-agento tool calling support."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest


class TestToolDefinitions:
    """Tests for ENCIK_TOOLS definitions."""

    def test_tools_have_required_fields(self):
        """Test tool definitions have required structure."""
        from A_agento.tools import ENCIK_TOOLS

        assert len(ENCIK_TOOLS) == 4
        names = [t["function"]["name"] for t in ENCIK_TOOLS]
        assert "search_encik" in names
        assert "get_encik_entry" in names
        assert "wikidata_property_id" in names
        assert "ensure_year_entry" in names

        for t in ENCIK_TOOLS:
            assert "parameters" in t["function"]
            assert "properties" in t["function"]["parameters"]
            assert "required" in t["function"]["parameters"]


class TestExecuteToolCall:
    """Tests for execute_tool_call."""

    def test_unknown_tool(self):
        """Test unknown tool returns error."""
        from A_agento.tools import execute_tool_call
        from A.core.providers import ToolCall

        tc = ToolCall(id="1", function={"name": "unknown", "arguments": "{}"})
        result = execute_tool_call(tc)
        data = json.loads(result)
        assert "error" in data

    def test_invalid_arguments(self):
        """Test invalid arguments returns error."""
        from A_agento.tools import execute_tool_call
        from A.core.providers import ToolCall

        tc = ToolCall(id="1", function={"name": "search_encik", "arguments": "not json"})
        result = execute_tool_call(tc)
        data = json.loads(result)
        assert "error" in data

    def test_search_encik_no_encik(self):
        """Test search returns error when A-encik not installed."""
        from A_agento.tools import execute_tool_call
        from A.core.providers import ToolCall

        tc = ToolCall(id="1", function={"name": "search_encik", "arguments": '{"query": "test"}'})
        result = execute_tool_call(tc)
        data = json.loads(result)
        assert "error" in data or "message" in data


class TestGenerateWithTools:
    """Tests for generate_with_tools orchestration."""

    def test_no_tool_calls_returns_content(self):
        """Test provider returning text without tool calls."""
        from A_agento.tools import generate_with_tools
        mock_provider = Mock()
        mock_provider.supports_tools = True
        mock_response = Mock()
        mock_response.content = "Final response"
        mock_response.tool_calls = None
        mock_provider.chat.return_value = mock_response

        result = generate_with_tools(mock_provider, [{"role": "user", "content": "hello"}])
        assert result == "Final response"

    def test_fallback_for_unsupported_providers(self):
        """Test fallback for providers without tool support."""
        from A_agento.tools import generate_with_tools
        mock_provider = Mock()
        mock_provider.supports_tools = False
        mock_provider.generate.return_value = "Fallback response"

        result = generate_with_tools(mock_provider, [{"role": "user", "content": "hello"}])
        assert result == "Fallback response"


class TestFallbackWithContext:
    """Tests for _fallback_with_context."""

    def test_keyword_extraction(self):
        """Test that keywords are extracted from user message."""
        with patch("A_agento.tools._search_encik", return_value='[]'):
            from A_agento.tools import _fallback_with_context

            mock_provider = Mock()
            mock_provider.generate.return_value = "Generated text"
            mock_provider.supports_tools = False

            result = _fallback_with_context(
                mock_provider,
                [{"role": "user", "content": "Explain quantum computing"}],
                [],
            )
            assert result == "Generated text"
