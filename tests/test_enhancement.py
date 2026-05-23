"""Tests for A-agento enhancement command (plibonigi)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import typer

import pytest
from typer.testing import CliRunner

from A_agento.cli import app
from A_agento.prompt_loader import clear_cache


runner = CliRunner()

# The plibonigi command imports get_provider_or_exit at module level, so we
# must patch at the consumer namespace (enhancement.py), not the definition
# location (_helpers.py).
_PATCH_TARGET = "A_agento.commands._enhancement_helpers.get_provider_or_exit"


class TestPlibonigiHelp:
    """Tests that the plibonigi command is properly registered."""

    def test_plibonigi_in_app_commands(self):
        """plibonigi should be registered as a top-level command."""
        names = [c.name for c in app.registered_commands if c.name]
        assert "plibonigi" in names

    def test_plibonigi_help(self):
        """--help should show plibonigi info."""
        result = runner.invoke(app, ["plibonigi", "--help"])
        assert result.exit_code == 0
        assert "plibonigi" in result.output.lower()
        assert "--formato" in result.output
        assert "--interjekti" in result.output
        assert "--konservi" in result.output
        assert "--ligilo" in result.output
        assert "--dosiero" in result.output

    def test_plibonigi_no_args(self):
        """Calling plibonigi without args and TTY should show error."""
        result = runner.invoke(app, ["plibonigi"])
        assert result.exit_code != 0
        assert "Error" in result.output or "eniga" in result.output


class TestPlibonigiStringInput:
    """Tests with string input."""

    @patch(_PATCH_TARGET)
    def test_basic_enhancement(self, mock_get_provider):
        """Enhance a simple string."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "This is enhanced text."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["plibonigi", "This needs improvement"])
        assert result.exit_code == 0
        assert "This is enhanced text." in result.output

    @patch(_PATCH_TARGET)
    def test_with_instruction(self, mock_get_provider):
        """Enhance with explicit instruction (positional)."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "I am writing a formal letter."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "plibonigi", "i'm writing a letter", "make more formal",
        ])
        assert result.exit_code == 0
        assert "I am writing a formal letter." in result.output

    @patch(_PATCH_TARGET)
    def test_with_provider(self, mock_get_provider):
        """Enhance with explicit provider."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced text."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "plibonigi", "Some text",
            "--provizanto", "ollama",
        ])
        assert mock_get_provider.called or result.exit_code == 0

    @patch(_PATCH_TARGET)
    def test_with_md_format(self, mock_get_provider):
        """Enhance with markdown format flag."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "## Enhanced\n\nBetter content."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "plibonigi", "## Original\n\nOld content.",
            "-f", "md",
        ])
        assert result.exit_code == 0
        assert "Enhanced" in result.output

    @patch(_PATCH_TARGET)
    def test_with_json_format(self, mock_get_provider):
        """Enhance with JSON format flag."""
        mock_provider = Mock()
        mock_provider.generate.return_value = '{"title": "Enhanced", "content": "Better text."}'
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "plibonigi", '{"title": "Original", "content": "Old text."}',
            "-f", "json",
        ])
        assert result.exit_code == 0
        assert '"title"' in result.output

    @patch(_PATCH_TARGET)
    def test_empty_string_error(self, mock_get_provider):
        """Empty or whitespace-only input should error."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["plibonigi", "   "])
        assert result.exit_code != 0

    @patch(_PATCH_TARGET)
    def test_invalid_format_error(self, mock_get_provider):
        """Invalid format should error."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "plibonigi", "some text",
            "-f", "invalid",
        ])
        assert result.exit_code != 0
        assert "Nevalida" in result.output or "Invalid" in result.output


class TestPlibonigiFileInput:
    """Tests with file input."""

    @patch(_PATCH_TARGET)
    def test_auto_detect_file(self, mock_get_provider, tmp_path):
        """Auto-detect file path as input."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced content."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "draft.txt"
        f.write_text("Original content.", encoding="utf-8")

        result = runner.invoke(app, ["plibonigi", str(f)])
        assert result.exit_code == 0
        assert "Enhanced content." in result.output

    @patch(_PATCH_TARGET)
    def test_explicit_dosiero_flag(self, mock_get_provider, tmp_path):
        """Explicit --dosiero flag reads file."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Improved text."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "input.txt"
        f.write_text("Needs improvement.", encoding="utf-8")

        result = runner.invoke(app, [
            "plibonigi", "ignored",
            "--dosiero", str(f),
        ])
        assert result.exit_code == 0
        assert "Improved text." in result.output

    def test_missing_file_error(self):
        """Non-existent file path should error."""
        result = runner.invoke(app, ["plibonigi", "/nonexistent/path/file.txt"])
        assert result.exit_code != 0


class TestPlibonigiStdin:
    """Tests for input resolution including stdin."""

    def test_resolve_input_text_stdin(self):
        """_resolve_input_text should read from stdin when not TTY."""
        from A_agento.commands.enhancement import _resolve_input_text

        with patch("A_agento.commands._enhancement_helpers._sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = "stdin content"

            result = _resolve_input_text("", None)
            assert result == "stdin content"

    def test_resolve_input_text_empty_no_stdin(self):
        """_resolve_input_text should error when no input and stdin is TTY."""
        from A_agento.commands.enhancement import _resolve_input_text

        with patch("A_agento.commands._enhancement_helpers._sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True

            with pytest.raises(typer.Exit):
                _resolve_input_text("", None)

    def test_resolve_input_text_string(self):
        """_resolve_input_text should return string arg as-is."""
        from A_agento.commands.enhancement import _resolve_input_text

        result = _resolve_input_text("direct text", None)
        assert result == "direct text"

    @patch(_PATCH_TARGET)
    def test_enhance_text_direct_works(self, mock_get_provider):
        """Enhance_text function can be called directly (stdin bypass)."""
        from A_agento.commands.enhancement import enhance_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = enhance_text("Input text.", instruction="test")
        assert result == "Enhanced."


class TestPlibonigiOutput:
    """Tests for output flags (--konservi, --kopii)."""

    @patch(_PATCH_TARGET)
    def test_konservi_flag(self, mock_get_provider, tmp_path):
        """--konservi saves result to file."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        out = tmp_path / "output.txt"
        result = runner.invoke(app, [
            "plibonigi", "Some text",
            "-K", str(out),
        ])
        assert result.exit_code == 0
        assert out.read_text() == "Enhanced."
        assert "Konservita" in result.output or "Saved" in result.output

    @patch(_PATCH_TARGET)
    def test_kopii_flag_string(self, mock_get_provider):
        """--kopii copies enhanced string to clipboard."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced text."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        with patch("A_agento.commands.enhancement.copy_to_clipboard") as mock_copy:
            result = runner.invoke(app, [
                "plibonigi", "Some text",
                "-k",
            ])
            assert result.exit_code == 0
            mock_copy.assert_called_once_with("Enhanced text.")

    @patch(_PATCH_TARGET)
    def test_kopii_flag_filepath(self, mock_get_provider, tmp_path):
        """--kopii with --konservi copies file path to clipboard."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        out = tmp_path / "out.txt"
        with patch("A_agento.commands.enhancement.copy_to_clipboard") as mock_copy:
            result = runner.invoke(app, [
                "plibonigi", "Some text",
                "-K", str(out),
                "-k",
            ])
            assert result.exit_code == 0
            saved_path = mock_copy.call_args[0][0]
            assert str(out) in saved_path or saved_path.endswith("out.txt")


class TestEnhanceTextFunction:
    """Tests for the importable enhance_text function."""

    @patch(_PATCH_TARGET)
    def test_enhance_text_basic(self, mock_get_provider):
        """enhance_text() with basic params."""
        from A_agento.commands.enhancement import enhance_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = enhance_text("Original text.")
        assert result == "Enhanced."

    @patch(_PATCH_TARGET)
    def test_enhance_text_with_instruction(self, mock_get_provider):
        """enhance_text() with instruction."""
        from A_agento.commands.enhancement import enhance_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "Formal improved text."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = enhance_text("improve this", instruction="make formal")
        assert result == "Formal improved text."

    @patch(_PATCH_TARGET)
    def test_enhance_text_md_format(self, mock_get_provider):
        """enhance_text() with md format."""
        from A_agento.commands.enhancement import enhance_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "## Enhanced\n\nBetter."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = enhance_text("## Original\n\nOld.", formato="md")
        assert result == "## Enhanced\n\nBetter."

    @patch(_PATCH_TARGET)
    def test_enhance_text_with_provider_ref(self, mock_get_provider):
        """enhance_text() with explicit provider_ref."""
        from A_agento.commands.enhancement import enhance_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "Result."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = enhance_text("Input.", provider_ref="ollama")
        assert mock_get_provider.called
        assert result == "Result."


class TestEncFormat:
    """Tests for enc format enhancement (tool-based)."""

    @patch(_PATCH_TARGET)
    @patch("A_agento.tools.generate_with_tools")
    def test_enc_format_calls_generate_with_tools(
        self, mock_generate_tools, mock_get_provider
    ):
        """enc format should use generate_with_tools (not basic generate)."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider
        mock_generate_tools.return_value = (
            "```enc\n"
            'terminologio.eo = "Test"\n'
            'difino.eo = "Enhanced."\n'
            "```"
        )

        from A_agento.commands.enhancement import enhance_text

        result = enhance_text(
            'terminologio.eo = "Test"\ndifino.eo = "Original."',
            instruction="expand",
            formato="enc",
        )
        assert mock_generate_tools.called
        # Should have stripped code fences (cleaned output)
        assert "terminologio.eo" in result
        assert "```" not in result

    @patch(_PATCH_TARGET)
    def test_enc_format_cli(self, mock_get_provider):
        """CLI enc format should accept enc flag."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        with patch("A_agento.tools.generate_with_tools") as mock_tools:
            mock_tools.return_value = (
                "terminologio.eo = \"Test\"\n"
                "difino.eo = \"Enhanced.\"\n"
            )
            result = runner.invoke(app, [
                "plibonigi", "terminologio.eo = \"Test\"",
                "-f", "enc",
            ])
            assert result.exit_code == 0
            assert mock_tools.called


class TestPromptTemplate:
    """Tests for the enhancement prompt template."""

    @patch(_PATCH_TARGET)
    def test_prompt_has_original_text(self, mock_get_provider):
        """Prompt should include the original text."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, ["plibonigi", "This is the original text"])
        call_args = mock_provider.generate.call_args[0][0]
        assert "This is the original text" in call_args

    @patch(_PATCH_TARGET)
    def test_prompt_has_instruction(self, mock_get_provider):
        """Prompt should include the enhancement instruction."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, [
            "plibonigi", "Some text", "make more formal",
        ])
        call_args = mock_provider.generate.call_args[0][0]
        assert "make more formal" in call_args

    @patch(_PATCH_TARGET)
    def test_prompt_has_format(self, mock_get_provider):
        """Prompt should include the format for non-enc."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, [
            "plibonigi", "# Header\n\nContent.",
            "-f", "md",
        ])
        call_args = mock_provider.generate.call_args[0][0]
        assert "md" in call_args or "markdown" in call_args.lower()

    @patch(_PATCH_TARGET)
    def test_prompt_empty_instruction(self, mock_get_provider):
        """Prompt without instruction should still work."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, [
            "plibonigi", "Some text",
        ])
        call_args = mock_provider.generate.call_args[0][0]
        # Should contain the original text
        assert "Some text" in call_args


class TestFormatInference:
    """Tests for auto-detection of format from file extension."""

    @patch(_PATCH_TARGET)
    def test_infer_md_from_extension(self, mock_get_provider, tmp_path):
        """--formato should be inferred as md from .md extension."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "# Enhanced"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "doc.md"
        f.write_text("# Original", encoding="utf-8")

        result = runner.invoke(app, [
            "plibonigi", str(f), "improve",
        ])
        assert result.exit_code == 0
        # Verify md was passed to prompt (format inference worked)
        call_args = mock_provider.generate.call_args[0][0]
        assert "md" in call_args or "markdown" in call_args.lower()

    @patch(_PATCH_TARGET)
    def test_infer_enc_from_extension(self, mock_get_provider, tmp_path):
        """--formato should be inferred as enc from .enc extension."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "entry.enc"
        f.write_text('terminologio.eo = "Test"', encoding="utf-8")

        with patch("A_agento.tools.generate_with_tools") as mock_tools:
            mock_tools.return_value = 'terminologio.eo = "Test"'
            result = runner.invoke(app, [
                "plibonigi", str(f), "expand",
            ])
            assert result.exit_code == 0
            assert mock_tools.called

    @patch(_PATCH_TARGET)
    def test_explicit_formato_overrides_inference(self, mock_get_provider, tmp_path):
        """Explicit --formato should override inference from extension."""
        mock_provider = Mock()
        mock_provider.generate.return_value = '{"title": "Enhanced"}'
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "notes.md"
        f.write_text("# Notes", encoding="utf-8")

        result = runner.invoke(app, [
            "plibonigi", str(f), "improve",
            "-f", "json",
        ])
        assert result.exit_code == 0
        # Format should be json, not md
        call_args = mock_provider.generate.call_args[0][0]
        assert "json" in call_args.lower()

    def test_infer_format_unknown_extension(self):
        """Unknown extension should not cause error (falls back to txt)."""
        from A_agento.commands.enhancement import _infer_format_from_input
        result = _infer_format_from_input("file.xyz", None)
        assert result is None


class TestInterjekti:
    """Tests for --interjekti / -i flag."""

    @patch(_PATCH_TARGET)
    def test_interjekti_flag_with_enc(self, mock_get_provider):
        """--interjekti / -i should be accepted (enc format uses it via tools)."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        with patch("A_agento.tools.generate_with_tools") as mock_tools:
            mock_tools.return_value = 'terminologio.eo = "Test"'
            result = runner.invoke(app, [
                "plibonigi", "terminologio.eo = \"Test\"",
                "-f", "enc",
                "-i",
            ])
            assert result.exit_code == 0

    @patch(_PATCH_TARGET)
    def test_interjekti_long_form(self, mock_get_provider):
        """--interjekti long form should work."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        with patch("A_agento.tools.generate_with_tools") as mock_tools:
            mock_tools.return_value = 'terminologio.eo = "Test"'
            result = runner.invoke(app, [
                "plibonigi", "terminologio.eo = \"Test\"",
                "-f", "enc",
                "--interjekti",
            ])
            assert result.exit_code == 0

    @patch(_PATCH_TARGET)
    def test_interjekti_no_conflict_with_instruction(self, mock_get_provider):
        """-i should be interjekti, not instruction — instruction is positional."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        with patch("A_agento.tools.generate_with_tools") as mock_tools:
            mock_tools.return_value = 'terminologio.eo = "Test"'
            # -i flag should NOT consume the positional instruction
            result = runner.invoke(app, [
                "plibonigi", "terminologio.eo = \"Test\"", "expand with details",
                "-f", "enc",
                "-i",
            ])
            assert result.exit_code == 0
            # Verify instruction "expand with details" was passed through
            msg = mock_tools.call_args[0][1][0]["content"]
            assert "expand with details" in msg


class TestPlibonigiStdinDisambiguation:
    """Tests for stdin+positional disambiguation."""

    @patch(_PATCH_TARGET)
    def test_stdin_with_instrukcio_option(self, mock_get_provider):
        """With stdin piping, use --instrukcio for the instruction."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced from stdin."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        # CliRunner input= sets stdin; isatty() returns False for BytesIO
        result = runner.invoke(app, [
            "plibonigi",
            "--instrukcio", "make this formal",
        ], input="piped content")
        assert result.exit_code == 0
        # The --instrukcio value should be the instruction
        call_args = mock_provider.generate.call_args[0][0]
        assert "make this formal" in call_args
        assert "piped content" in call_args


class TestPlibonigiLigilo:
    """Tests for --ligilo flag."""

    @patch(_PATCH_TARGET)
    @patch("A_agento.commands.enhancement._core_html_to_text", None)
    @patch("A_agento.commands.enhancement._fetch_text")
    def test_ligilo_fetches_url(self, mock_fetch, mock_get_provider, tmp_path):
        """--ligilo should fetch URL content."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Enhanced with context."
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider
        mock_fetch.return_value = "<html><body>Web content.</body></html>"

        result = runner.invoke(app, [
            "plibonigi", "Enhance this",
            "--ligilo", "https://example.com",
        ])
        assert result.exit_code == 0

    def test_ligilo_without_http_module(self):
        """--ligilo without A-core http module should error."""
        with patch("A_agento.commands.enhancement._fetch_text", None):
            result = runner.invoke(app, [
                "plibonigi", "text",
                "--ligilo", "https://example.com",
            ])
            assert result.exit_code != 0
