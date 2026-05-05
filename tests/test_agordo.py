"""Tests for A-agento agordo (provider configuration) commands."""

from __future__ import annotations

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


class TestAldoniCommand:
    """Tests for `agordo aldoni` (formerly slosilo)."""

    def test_aldoni_shows_help(self):
        """Test aldoni subcommand shows help."""
        result = runner.invoke(app, ["agordo", "aldoni", "--help"])
        assert result.exit_code == 0
        assert "aldoni" in result.output.lower()

    @patch("A_agento.agordo.set_default_provider")
    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.save_provider_config")
    @patch("A_agento.agordo.save_api_key")
    def test_aldoni_with_key(
        self, mock_save_key, mock_save_cfg, mock_list, mock_set_default
    ):
        """Test adding a key with --key option."""
        mock_list.return_value = []  # No existing configs
        mock_save_key.return_value = True

        result = runner.invoke(
            app,
            [
                "agordo", "aldoni", "openai",
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
        mock_set_default.assert_called_once_with("openai")

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.save_provider_config")
    @patch("A_agento.agordo.save_api_key")
    def test_aldoni_with_base_url(
        self, mock_save_key, mock_save_cfg, mock_list
    ):
        """Test adding a key with custom base URL."""
        mock_list.return_value = [{"provider": "ollama"}]  # Existing config
        mock_save_key.return_value = True

        result = runner.invoke(
            app,
            [
                "agordo", "aldoni", "openai",
                "--key", "sk-test123",
                "--base-url", "https://custom.endpoint/v1",
            ],
        )
        assert result.exit_code == 0
        mock_save_key.assert_called_once_with(
            "sk-test123", provider="openai", profile="default"
        )

    def test_aldoni_ollama_warns(self):
        """Test aldoni with ollama shows warning."""
        result = runner.invoke(
            app,
            ["agordo", "aldoni", "ollama", "--key", "dummy"],
        )
        assert result.exit_code == 0
        assert "Ollama" in result.output

    def test_aldoni_custom_provider(self):
        """Test aldoni accepts custom provider names (OpenAI-compatible)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"), \
             patch("A_agento.agordo.list_provider_configs", return_value=[]), \
             patch("A_agento.agordo.set_default_provider"):
            result = runner.invoke(
                app,
                ["agordo", "aldoni", "my-custom-endpoint", "--key", "test"],
            )
            assert result.exit_code == 0
            assert "konservita" in result.output or "saved" in result.output

    def test_aldoni_missing_provider(self):
        """Test aldoni without provider argument."""
        result = runner.invoke(app, ["agordo", "aldoni"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestVidiCommand:
    """Tests for `agordo vidi`."""

    def test_vidi_shows_help(self):
        """Test vidi subcommand shows help."""
        result = runner.invoke(app, ["agordo", "vidi", "--help"])
        assert result.exit_code == 0
        assert "vidi" in result.output.lower()

    @patch("A_agento.agordo_crud.get_api_key")
    @patch("A_agento.agordo_crud.get_provider_config")
    def test_vidi_existing(self, mock_get_cfg, mock_get_key):
        """Test viewing an existing provider."""
        mock_get_cfg.return_value = {
            "provider": "openai",
            "profile": "default",
            "modelo": "gpt-4",
            "base_url": "https://api.openai.com/v1",
            "noto": "work",
            "kreita_je": "2024-01-01T00:00:00",
            "modifita_je": "2024-01-02T00:00:00",
        }
        mock_get_key.return_value = "sk-test123"

        result = runner.invoke(app, ["agordo", "vidi", "openai"])
        assert result.exit_code == 0
        assert "openai" in result.output.lower()

    @patch("A_agento.agordo_crud.get_provider_config", return_value=None)
    def test_vidi_not_found(self, mock_get_cfg):
        """Test viewing a non-existent provider."""
        result = runner.invoke(app, ["agordo", "vidi", "nonexistent"])
        assert result.exit_code != 0
        assert "ne trovita" in result.output.lower() or "not found" in result.output.lower()


class TestModifiCommand:
    """Tests for `agordo modifi`."""

    def test_modifi_shows_help(self):
        """Test modifi subcommand shows help."""
        result = runner.invoke(app, ["agordo", "modifi", "--help"])
        assert result.exit_code == 0
        assert "modifi" in result.output.lower()

    @patch("A_agento.agordo_crud.get_provider_config")
    @patch("A_agento.agordo_crud.save_provider_config")
    def test_modifi_not_found(self, mock_save_cfg, mock_get_cfg):
        """Test modifying a non-existent provider."""
        mock_get_cfg.return_value = None
        result = runner.invoke(app, ["agordo", "modifi", "nonexistent"])
        assert result.exit_code != 0

    @patch("A_agento.agordo_crud.get_provider_config")
    @patch("A_agento.agordo_crud.save_provider_config")
    def test_modifi_update_base_url(self, mock_save_cfg, mock_get_cfg):
        """Test modifying base URL of an existing provider."""
        mock_get_cfg.return_value = {
            "provider": "openai",
            "profile": "default",
            "modelo": "gpt-4",
            "base_url": "https://old.endpoint/v1",
            "noto": "",
        }

        result = runner.invoke(
            app,
            ["agordo", "modifi", "openai", "--base-url", "https://new.endpoint/v1"],
        )
        assert result.exit_code == 0


class TestForigiCommand:
    """Tests for `agordo forigi`."""

    def test_forigi_shows_help(self):
        """Test forigi subcommand shows help."""
        result = runner.invoke(app, ["agordo", "forigi", "--help"])
        assert result.exit_code == 0
        assert "forigi" in result.output.lower()

    def test_forigi_not_found(self):
        """Test deleting a non-existent provider."""
        result = runner.invoke(app, ["agordo", "forigi", "nonexistent"])
        assert result.exit_code == 0
        assert "ne trovita" in result.output.lower() or "not found" in result.output.lower()

    @patch("A_agento.agordo_crud._delete_provider_config", return_value=True)
    @patch("A_agento.agordo_crud._find_config")
    @patch("A_agento.agordo_crud._maybe_reassign_default")
    def test_forigi_with_yes(
        self, mock_reassign, mock_find, mock_del
    ):
        """Test deleting a provider with -y flag."""
        mock_find.return_value = {
            "provider": "openai",
            "profile": "default",
        }

        result = runner.invoke(
            app,
            ["agordo", "forigi", "openai", "-y"],
        )
        assert result.exit_code == 0


class TestDeprecatedAliases:
    """Tests for deprecated slosilo/sxlosilo aliases."""

    def test_slosilo_deprecated_works(self):
        """Test slosilo still works (calls aldoni under the hood)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"), \
             patch("A_agento.agordo.list_provider_configs", return_value=[]), \
             patch("A_agento.agordo.set_default_provider"):
            result = runner.invoke(
                app,
                ["agordo", "slosilo", "openai", "--key", "test"],
            )
            assert result.exit_code == 0

    def test_sxlosilo_deprecated_works(self):
        """Test sxlosilo still works (calls aldoni under the hood)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"), \
             patch("A_agento.agordo.list_provider_configs", return_value=[]), \
             patch("A_agento.agordo.set_default_provider"):
            result = runner.invoke(
                app,
                ["agordo", "sxlosilo", "openai", "--key", "test"],
            )
            assert result.exit_code == 0


class TestMontriCommand:
    """Tests for `agordo ls` (formerly montri)."""

    def test_ls_shows_help(self):
        """Test ls subcommand shows help."""
        result = runner.invoke(app, ["agordo", "ls", "--help"])
        assert result.exit_code == 0
        assert "ls" in result.output.lower()

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.get_default_provider")
    def test_ls_no_configs(self, mock_default, mock_list):
        """Test ls when no providers configured."""
        mock_default.return_value = "ollama"
        mock_list.return_value = []

        result = runner.invoke(app, ["agordo", "ls"])
        assert result.exit_code == 0
        assert "Neniuj" in result.output or "No" in result.output

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.agordo.get_default_provider")
    def test_ls_with_configs(self, mock_default, mock_list):
        """Test ls with configured providers."""
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

        result = runner.invoke(app, ["agordo", "ls"])
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
        assert result.exit_code != 0

    def test_agordo_help(self):
        """Test agordo --help shows subcommands."""
        result = runner.invoke(app, ["agordo", "--help"])
        assert result.exit_code == 0
        assert "default" in result.output
        assert "aldoni" in result.output
        assert "vidi" in result.output
        assert "modifi" in result.output
        assert "forigi" in result.output
        assert "ls" in result.output
        assert "testi" in result.output
