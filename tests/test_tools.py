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

        assert len(ENCIK_TOOLS) == 5
        names = [t["function"]["name"] for t in ENCIK_TOOLS]
        assert "search_encik" in names
        assert "get_encik_entry" in names
        assert "wikidata_property_id" in names
        assert "ensure_decade" in names
        assert "ensure_century" in names

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

    def test_search_encik_returns_list(self):
        """Test search returns a list of results."""
        from A_agento.tools import execute_tool_call
        from A.core.providers import ToolCall

        with patch("A_agento.tools.executor._search_encik", return_value='[{"uuid": "abc", "titolo": "test"}]'):
            tc = ToolCall(id="1", function={"name": "search_encik", "arguments": '{"query": "test"}'})
            result = execute_tool_call(tc)
            data = json.loads(result)
            assert isinstance(data, list)


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
        mock_response = Mock()
        mock_response.content = "Fallback response"
        mock_provider.chat.return_value = mock_response

        result = generate_with_tools(mock_provider, [{"role": "user", "content": "hello"}])
        assert result == "Fallback response"

    def test_max_turns_with_tool_calls_forces_final_gen(self):
        """When max_turns exhausted with tool_calls, force final generation without tools."""
        from A_agento.tools import generate_with_tools
        from A.core.providers import ToolCall

        mock_provider = Mock()
        mock_provider.supports_tools = True

        # Response with tool_calls (never generating final content on its own)
        tool_response = Mock()
        tool_response.content = None
        tool_response.tool_calls = [
            ToolCall(id="1", type="function", function={
                "name": "search_encik", "arguments": '{"query": "test"}'
            }),
        ]
        tool_response.reasoning_content = None

        # Final forced generation response (after max_turns exhausted)
        final_response = Mock()
        final_response.content = "terminologio.eo = \"test\""
        final_response.tool_calls = None

        # max_turns=2: both turns return tool_calls, then force final gen
        mock_provider.chat.side_effect = [
            tool_response,   # turn 0 → tool_calls → process → continue
            tool_response,   # turn 1 → tool_calls → max_turns exhausted
            final_response,  # forced final gen without tools
        ]

        result = generate_with_tools(
            mock_provider, [{"role": "user", "content": "test"}],
            tools=[], max_turns=2,
        )
        assert result == 'terminologio.eo = "test"'
        # Verify the forced call used tools=None
        last_call_kwargs = mock_provider.chat.call_args_list[-1][1]
        assert last_call_kwargs.get("tools") is None

    def test_raw_output_retry_escalates(self):
        """Test raw output retry sends escalating messages (not just repeat)."""
        from A_agento.tools import generate_with_tools

        mock_provider = Mock()
        mock_provider.supports_tools = True

        raw_response = Mock()
        raw_response.content = '[{"uuid": "abc", "titolo": "test"}]'
        raw_response.tool_calls = None

        final_response = Mock()
        final_response.content = "terminologio.eo = \"generated\""
        final_response.tool_calls = None

        # Three raw outputs (escalating through all 3 messages), then final
        mock_provider.chat.side_effect = [raw_response, raw_response, raw_response, final_response]

        result = generate_with_tools(
            mock_provider, [{"role": "user", "content": "test"}],
            tools=[], max_turns=5,
        )
        assert result == 'terminologio.eo = "generated"'
        # Verify that escalating messages were sent (the last user message should be forceful)
        calls = mock_provider.chat.call_args_list
        user_msgs = [
            msg["content"]
            for call in calls
            for msg in call[0][0]
            if msg["role"] == "user"
        ]
        # After 3 raw output detections, the retry message should escalate to "STOP"
        stop_msgs = [m for m in user_msgs if m.startswith("STOP")]
        assert len(stop_msgs) > 0
        # Verify messages are different (escalating, not identical repeats)
        unique_retry_msgs = set(
            m for m in user_msgs
            if m != "test"  # exclude original user prompt
        )
        assert len(unique_retry_msgs) >= 2  # at least 2 distinct retry messages

    def test_max_turns_exhausted_raw_output_falls_through(self):
        """Combined: max_turns exhausted + raw output → safety net forces final gen."""
        from A_agento.tools import generate_with_tools
        from A.core.providers import ToolCall

        mock_provider = Mock()
        mock_provider.supports_tools = True

        tool_response = Mock()
        tool_response.content = None
        tool_response.tool_calls = [
            ToolCall(id="1", type="function", function={
                "name": "search_encik", "arguments": '{"query": "test"}'
            }),
        ]
        tool_response.reasoning_content = None

        raw_response = Mock()
        raw_response.content = '[{"uuid": "abc"}]'
        raw_response.tool_calls = None

        final_response = Mock()
        final_response.content = "terminologio.eo = \"final\""
        final_response.tool_calls = None

        # max_turns=2: turn 0 → tool_calls, turn 1 → raw → retry → loop ends
        mock_provider.chat.side_effect = [
            tool_response,   # turn 0 → tool_calls → process → continue
            raw_response,    # turn 1 → raw output → retry → loop ends
            final_response,  # safety net: force final gen without tools
        ]

        result = generate_with_tools(
            mock_provider, [{"role": "user", "content": "test"}],
            tools=[], max_turns=2,
        )
        assert result == 'terminologio.eo = "final"'
        last_call_kwargs = mock_provider.chat.call_args_list[-1][1]
        assert last_call_kwargs.get("tools") is None

    def test_empty_content_at_max_turns(self):
        """Empty content after max_turns → safety net forces final gen."""
        from A_agento.tools import generate_with_tools
        from A.core.providers import ToolCall

        mock_provider = Mock()
        mock_provider.supports_tools = True

        tool_response = Mock()
        tool_response.content = None
        tool_response.tool_calls = [
            ToolCall(id="1", type="function", function={
                "name": "search_encik", "arguments": '{"query": "test"}'
            }),
        ]
        tool_response.reasoning_content = None

        empty_response = Mock()
        empty_response.content = ""
        empty_response.tool_calls = None

        final_response = Mock()
        final_response.content = "Generated fallback content"
        final_response.tool_calls = None

        # max_turns=2: turn 0 → tool_calls, turn 1 → empty content
        mock_provider.chat.side_effect = [
            tool_response,   # turn 0 → tool_calls → process → continue
            empty_response,  # turn 1 → empty → not raw (but empty) → return? no... 
        ]

        # Wait: empty content is caught by is_raw_tool_output("") which returns True
        # So turn 1: raw_output_retries=1, retry message appended, continue
        # But continue tries turn 2, max_turns=2 → loop ends
        # After loop: response = empty_response
        # response.tool_calls is None → content = ""
        # Safety net: not content → True → force final gen
        mock_provider.chat.side_effect = [
            tool_response,   # turn 0 → tool_calls
            empty_response,  # turn 1 → empty → retry → loop ends
            final_response,  # safety net: force final gen
        ]

        result = generate_with_tools(
            mock_provider, [{"role": "user", "content": "test"}],
            tools=[], max_turns=2,
        )
        assert result == "Generated fallback content"
        last_call_kwargs = mock_provider.chat.call_args_list[-1][1]
        assert last_call_kwargs.get("tools") is None


class TestFallbackWithContext:
    """Tests for _fallback_with_context."""

    def test_keyword_extraction(self):
        """Test that keywords are extracted from user message."""
        from A_agento.tools.executor import _fallback_with_context

        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "Generated text"
        mock_provider.chat.return_value = mock_response
        mock_provider.supports_tools = False

        result = _fallback_with_context(
            mock_provider,
            [{"role": "user", "content": "Explain quantum computing"}],
            [],
        )
        assert result == "Generated text"


class TestOfferTrafilatura:
    """_offer_trafilatura_if_missing delegates to ensure_dependency."""

    def test_trafilatura_available(self) -> None:
        """When trafilatura is already importable, no install needed."""
        from A_agento.commands._context_helpers import _offer_trafilatura_if_missing

        import types
        mock_mod = types.ModuleType("trafilatura")
        with patch.dict("sys.modules", {"trafilatura": mock_mod}):
            # Should return without attempting install
            _offer_trafilatura_if_missing()

    def test_calls_ensure_dependency(self) -> None:
        """When missing, calls ensure_dependency('trafilatura')."""
        from A_agento.commands._context_helpers import _offer_trafilatura_if_missing

        import builtins
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "trafilatura":
                raise ImportError
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", fake_import):
            with patch("A.utils.deps.ensure_dependency") as mock_ed:
                _offer_trafilatura_if_missing()
                mock_ed.assert_called_once_with("trafilatura")

    def test_import_error_shows_warning(self) -> None:
        """When ensure_dependency fails, shows warning instead of crashing."""
        from A_agento.commands._context_helpers import _offer_trafilatura_if_missing

        import builtins
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "trafilatura":
                raise ImportError
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", fake_import):
            with patch("A.utils.deps.ensure_dependency", side_effect=ImportError("fail")):
                with patch("A_agento.commands._context_helpers.warning") as mock_warn:
                    _offer_trafilatura_if_missing()
                    mock_warn.assert_called_once()
