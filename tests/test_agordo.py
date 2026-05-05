"""Tests for A-agento agordo (provider configuration) commands."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from A_agento.cli import app


runner = CliRunner()


class TestDefaultCommand:
    """Tests for `agordo default`."""

    def test_default_shows_help(self):
        """Test default subcommand shows help."""
        result = runner.invoke(app, ["agordo", "default", "--help"])
        assert result.exit_code == 0
        assert "default" in result.output.lower()

    @patch("A_agento.agordo.set_default_provider")
    def test_default_valid_provider(self, mock_set):
        """Test setting a valid provider."""
        result = runner.invoke(app, ["agordo", "default", "openai"])
        assert result.exit_code == 0
        mock_set.assert_called_once_with("openai")

    @patch("A_agento.agordo.set_default_provider")
    def test_default_ollama(self, mock_set):
        """Test setting ollama as default."""
        result = runner.invoke(app, ["agordo", "default", "ollama"])
        assert result.exit_code == 0
        mock_set.assert_called_once_with("ollama")

    def test_default_invalid_provider(self):
        """Test invalid provider name."""
        result = runner.invoke(app, ["agordo", "default", "invalid"])
        assert result.exit_code != 0
        assert "Nevalida" in result.output or "Invalid" in result.output


class TestSlosiloCommand:
    """Tests for `agordo slosilo`."""

    def test_slosilo_shows_help(self):
        """Test slosilo subcommand shows help."""
        result = runner.invoke(app, ["agordo", "slosilo", "--help"])
        assert result.exit_code == 0
        assert "slosilo" in result.output.lower()

    @patch("A_agento.agordo.save_api_key")
    @patch("A_agento.agordo.save_provider_config")
    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.set_default_provider")
    def test_slosilo_with_key(
        self, mock_set_default, mock_list, mock_save_cfg, mock_save_key
    ):
        """Test configuring a key with --key option."""
        mock_list.return_value = []  # No existing configs
        mock_save_key.return_value = True

        result = runner.invoke(
            app,
            [
                "agordo", "slosilo", "openai",
                "--key", "sk-test123",
                "--noto", "work",
                "--modelo", "gpt-4",
            ],
        )
        assert result.exit_code == 0
        mock_save_key.assert_called_once_with(
            "sk-test123", provider="openai", profile="work"
        )
        mock_save_cfg.assert_called_once()
        # Should set as default since no existing configs
        mock_set_default.assert_called_once_with("openai")

    @patch("A_agento.agordo.save_api_key")
    @patch("A_agento.agordo.save_provider_config")
    @patch("A_agento.agordo.list_provider_configs")
    def test_slosilo_with_base_url(
        self, mock_list, mock_save_cfg, mock_save_key
    ):
        """Test configuring a key with custom base URL."""
        mock_list.return_value = [{"provider": "ollama"}]  # Existing config
        mock_save_key.return_value = True

        result = runner.invoke(
            app,
            [
                "agordo", "slosilo", "openai",
                "--key", "sk-test123",
                "--base-url", "https://custom.endpoint/v1",
            ],
        )
        assert result.exit_code == 0
        mock_save_key.assert_called_once_with(
            "sk-test123", provider="openai", profile="default"
        )

    def test_slosilo_ollama_warns(self):
        """Test slosilo with ollama shows warning."""
        result = runner.invoke(
            app,
            ["agordo", "slosilo", "ollama", "--key", "dummy"],
        )
        assert result.exit_code == 0
        assert "Ollama" in result.output

    def test_slosilo_custom_provider(self):
        """Test slosilo accepts custom provider names (OpenAI-compatible)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"), \
             patch("A_agento.agordo.list_provider_configs", return_value=[]), \
             patch("A_agento.agordo.set_default_provider"):
            result = runner.invoke(
                app,
                ["agordo", "slosilo", "my-custom-endpoint", "--key", "test"],
            )
            assert result.exit_code == 0
            assert "konservita" in result.output or "saved" in result.output

    def test_slosilo_missing_provider(self):
        """Test slosilo without provider argument."""
        result = runner.invoke(app, ["agordo", "slosilo"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestMontriCommand:
    """Tests for `agordo montri`."""

    def test_montri_shows_help(self):
        """Test ls (formerly montri) subcommand shows help."""
        result = runner.invoke(app, ["agordo", "ls", "--help"])
        assert result.exit_code == 0
        assert "ls" in result.output.lower()

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.get_default_provider")
    def test_montri_no_configs(self, mock_default, mock_list):
        """Test montri when no providers configured."""
        mock_default.return_value = "ollama"
        mock_list.return_value = []

        result = runner.invoke(app, ["agordo", "montri"])
        assert result.exit_code == 0
        assert "Neniuj" in result.output or "No" in result.output

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.get_default_provider")
    def test_montri_with_configs(self, mock_default, mock_list):
        """Test montri with configured providers."""
        mock_default.return_value = "openai"
        mock_list.return_value = [
            {
                "provider": "openai",
                "profile": "default",
                "modelo": "gpt-4",
                "base_url": "",
                "noto": "",
            }
        ]

        result = runner.invoke(app, ["agordo", "montri"])
        assert result.exit_code == 0


class TestTestiCommand:
    """Tests for `agordo testi`."""

    def test_testi_shows_help(self):
        """Test testi subcommand shows help."""
        result = runner.invoke(app, ["agordo", "testi", "--help"])
        assert result.exit_code == 0
        assert "testi" in result.output.lower()

    @patch("A_agento.agordo.get_provider")
    def test_testi_success(self, mock_get_provider):
        """Test successful provider test."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.generate.return_value = " OK "
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["agordo", "testi"])
        assert result.exit_code == 0
        assert "sukcese" in result.output or "successfully" in result.output

    @patch("A_agento.agordo.get_provider")
    def test_testi_unexpected_response(self, mock_get_provider):
        """Test provider returns unexpected response."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.generate.return_value = "Hello world"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["agordo", "testi"])
        assert result.exit_code == 0

    @patch("A_agento.agordo.get_provider")
    def test_testi_error(self, mock_get_provider):
        """Test provider raises error."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.generate.side_effect = ConnectionError("Connection refused")
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["agordo", "testi"])
        assert result.exit_code != 0
        assert "eraro" in result.output or "error" in result.output


class TestAgordoGroup:
    """Tests for agordo group behavior."""

    def test_agordo_shows_help_without_args(self):
        """Test agordo without args shows help."""
        result = runner.invoke(app, ["agordo"])
        # Typer shows help and exits with 2 when no subcommand given
        assert result.exit_code != 0

    def test_agordo_help(self):
        """Test agordo --help shows subcommands."""
        result = runner.invoke(app, ["agordo", "--help"])
        assert result.exit_code == 0
        assert "default" in result.output
        assert "slosilo" in result.output
        assert "ls" in result.output
        assert "testi" in result.output
