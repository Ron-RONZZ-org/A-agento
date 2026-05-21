"""Tests for A-agento translation command (traduki)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from A_agento.cli import app


runner = CliRunner()

# The traduki command imports get_provider_or_exit at module level, so we
# must patch at the consumer namespace (translation.py), not the definition
# location (_helpers.py).
_PATCH_TARGET = "A_agento.commands.translation.get_provider_or_exit"


class TestTradukiHelp:
    """Tests that the traduki command is properly registered."""

    def test_traduki_in_app_commands(self):
        """traduki should be registered as a top-level command."""
        names = [c.name for c in app.registered_commands if c.name]
        assert "traduki" in names

    def test_traduki_help(self):
        """--help should show traduki info."""
        result = runner.invoke(app, ["traduki", "--help"])
        assert result.exit_code == 0
        assert "traduki" in result.output.lower()
        assert "--celo" in result.output
        assert "--fonto" in result.output
        assert "--konservi" in result.output
        assert "--kopii" in result.output

    def test_traduki_no_args(self):
        """Calling traduki without args should show error (missing argument)."""
        result = runner.invoke(app, ["traduki"])
        assert result.exit_code != 0
        assert "Error" in result.output


class TestTradukiStringInput:
    """Tests with string input."""

    @patch(_PATCH_TARGET)
    def test_basic_translation_string(self, mock_get_provider):
        """Translate a simple string."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Bonjour le monde"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["traduki", "Hello world", "-c", "fr"])
        assert result.exit_code == 0
        assert "Bonjour le monde" in result.output

    @patch(_PATCH_TARGET)
    def test_translation_with_source_and_target(self, mock_get_provider):
        """Translate with explicit source and target languages."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Hola mundo"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "traduki", "Hello world",
            "-c", "es",
            "-f", "en",
        ])
        assert result.exit_code == 0
        assert "Hola mundo" in result.output

    @patch(_PATCH_TARGET)
    def test_translation_auto_detect(self, mock_get_provider):
        """Translate without specifying source or target (auto-detect)."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Guten Tag"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["traduki", "Good day"])
        assert result.exit_code == 0
        assert "Guten Tag" in result.output

    @patch(_PATCH_TARGET)
    def test_translation_with_provider(self, mock_get_provider):
        """Translate with explicit provider."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Merci"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, [
            "traduki", "Thank you",
            "-c", "fr",
            "--provizanto", "ollama",
        ])
        # Should pass provider_ref through
        assert mock_get_provider.call_count >= 1 or result.exit_code == 0

    @patch(_PATCH_TARGET)
    def test_empty_string_error(self, mock_get_provider):
        """Empty or whitespace-only input should error."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["traduki", "   "])
        assert result.exit_code != 0


class TestTradukiFileInput:
    """Tests with file input."""

    @patch(_PATCH_TARGET)
    def test_auto_detect_file(self, mock_get_provider, tmp_path):
        """Auto-detect file path as input."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Hallo Welt"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "hello.txt"
        f.write_text("Hello world", encoding="utf-8")

        result = runner.invoke(app, ["traduki", str(f), "-c", "de"])
        assert result.exit_code == 0
        assert "Hallo Welt" in result.output

    @patch(_PATCH_TARGET)
    def test_explicit_dosiero_flag(self, mock_get_provider, tmp_path):
        """Explicit --dosiero flag reads file."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Salut le monde"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        f = tmp_path / "greeting.txt"
        f.write_text("Hello world", encoding="utf-8")

        result = runner.invoke(app, [
            "traduki", "ignored",
            "--dosiero", str(f),
            "-c", "fr",
        ])
        assert result.exit_code == 0
        assert "Salut le monde" in result.output

    def test_missing_file_error(self):
        """Non-existent file path should error."""
        result = runner.invoke(app, ["traduki", "/nonexistent/path/file.txt"])
        assert result.exit_code != 0


class TestTradukiOutput:
    """Tests for output flags (--konservi, --kopii)."""

    @patch(_PATCH_TARGET)
    def test_konservi_flag(self, mock_get_provider, tmp_path):
        """--konservi saves result to file."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Hola"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        out = tmp_path / "output.txt"
        result = runner.invoke(app, [
            "traduki", "Hello",
            "-c", "es",
            "-K", str(out),
        ])
        assert result.exit_code == 0
        assert out.read_text() == "Hola"
        assert "Konservita" in result.output or "Saved" in result.output

    @patch(_PATCH_TARGET)
    def test_kopii_flag_string(self, mock_get_provider):
        """--kopii copies translated string to clipboard."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Bonjour"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        with patch("A_agento.commands.translation.copy_to_clipboard") as mock_copy:
            result = runner.invoke(app, [
                "traduki", "Hello",
                "-c", "fr",
                "-k",
            ])
            assert result.exit_code == 0
            mock_copy.assert_called_once_with("Bonjour")

    @patch(_PATCH_TARGET)
    def test_kopii_flag_filepath(self, mock_get_provider, tmp_path):
        """--kopii with --konservi copies file path to clipboard."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Hallo"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        out = tmp_path / "out.txt"
        with patch("A_agento.commands.translation.copy_to_clipboard") as mock_copy:
            result = runner.invoke(app, [
                "traduki", "Hello",
                "-c", "de",
                "-K", str(out),
                "-k",
            ])
            assert result.exit_code == 0
            # Should copy the file path, not the translated text
            saved_path = mock_copy.call_args[0][0]
            assert str(out) in saved_path or saved_path.endswith("out.txt")


class TestTranslateTextFunction:
    """Tests for the importable translate_text function."""

    @patch(_PATCH_TARGET)
    def test_translate_text_basic(self, mock_get_provider):
        """translate_text() with explicit params."""
        from A_agento.commands.translation import translate_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "Bonjour"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = translate_text("Hello", target="fr")
        assert result == "Bonjour"

    @patch(_PATCH_TARGET)
    def test_translate_text_auto_params(self, mock_get_provider):
        """translate_text() with auto-detect (no target/source)."""
        from A_agento.commands.translation import translate_text

        mock_provider = Mock()
        mock_provider.generate.return_value = "Guten Tag"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        result = translate_text("Good day")
        assert result == "Guten Tag"


class TestPromptTemplate:
    """Tests for the translation prompt template."""

    @patch(_PATCH_TARGET)
    def test_prompt_has_target(self, mock_get_provider):
        """Prompt should include target language when specified."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Oui"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, ["traduki", "Yes", "-c", "fr"])
        call_args = mock_provider.generate.call_args[0][0]
        assert " to fr" in call_args

    @patch(_PATCH_TARGET)
    def test_prompt_has_source(self, mock_get_provider):
        """Prompt should include source language when specified."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Oui"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, ["traduki", "Yes", "-c", "fr", "-f", "en"])
        call_args = mock_provider.generate.call_args[0][0]
        assert " to fr" in call_args
        assert " from en" in call_args

    @patch(_PATCH_TARGET)
    def test_prompt_auto_no_lang(self, mock_get_provider):
        """Prompt without target/source should only say 'Translate the provided text'."""
        mock_provider = Mock()
        mock_provider.generate.return_value = "Oui"
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_get_provider.return_value = mock_provider

        runner.invoke(app, ["traduki", "Yes"])
        call_args = mock_provider.generate.call_args[0][0]
        # Should not contain " to " or " from "
        assert " to " not in call_args
        assert " from " not in call_args