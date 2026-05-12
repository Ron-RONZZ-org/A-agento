"""Tests for A-agento agordi (provider configuration) commands."""

from __future__ import annotations

from unittest.mock import Mock, patch
from typer.testing import CliRunner

from A_agento.cli import app


runner = CliRunner()


class TestDefaultCommand:
    """Tests for `agordi default`."""

    def test_default_shows_help(self):
        """Test default subcommand shows help."""
        result = runner.invoke(app, ["agordi", "default", "--help"])
        assert result.exit_code == 0
        assert "default" in result.output.lower()

    def test_default_not_configured(self):
        """Test default on a provider that has no config yet."""
        with patch("A_agento.agordo.find_config", return_value=None):
            result = runner.invoke(app, ["agordi", "default", "openai"])
            assert result.exit_code != 0
            assert "ne estas agordita" in result.output.lower() or "not configured" in result.output.lower()

    def test_default_sets_prioritato(self):
        """Test default sets prioritato=0 and shifts others."""
        mock_config = {"uuid": "abc123", "provider": "openai", "profile": "default"}
        with patch("A_agento.agordo.find_config", return_value=mock_config), \
             patch("A_agento.data.provider_config.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            result = runner.invoke(app, ["agordi", "default", "openai"])
            assert result.exit_code == 0
            # Should update prioritato=0 for openai, shift others
            assert mock_db.execute.call_count >= 2

    def test_default_invalid_provider(self):
        """Test invalid provider name."""
        result = runner.invoke(app, ["agordi", "default", "invalid"])
        assert result.exit_code != 0
        assert "Nevalida" in result.output or "Invalid" in result.output


class TestAldoniCommand:
    """Tests for `agordi aldoni` (formerly slosilo)."""

    def test_aldoni_shows_help(self):
        """Test aldoni subcommand shows help."""
        result = runner.invoke(app, ["agordi", "aldoni", "--help"])
        assert result.exit_code == 0
        assert "aldoni" in result.output.lower()

    @patch("A_agento.agordo.save_provider_config")
    @patch("A_agento.agordo.save_api_key")
    def test_aldoni_with_key(
        self, mock_save_key, mock_save_cfg
    ):
        """Test adding a key with --key option."""
        mock_save_key.return_value = True

        result = runner.invoke(
            app,
            [
                "agordi", "aldoni", "openai",
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

    @patch("A_agento.agordo.save_provider_config")
    @patch("A_agento.agordo.save_api_key")
    def test_aldoni_with_base_url(
        self, mock_save_key, mock_save_cfg
    ):
        """Test adding a key with custom base URL."""
        mock_save_key.return_value = True

        result = runner.invoke(
            app,
            [
                "agordi", "aldoni", "openai",
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
            ["agordi", "aldoni", "ollama", "--key", "dummy"],
        )
        assert result.exit_code == 0
        assert "Ollama" in result.output

    def test_aldoni_custom_provider(self):
        """Test aldoni accepts custom provider names (OpenAI-compatible)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"):
            result = runner.invoke(
                app,
                ["agordi", "aldoni", "my-custom-endpoint", "--key", "test"],
            )
            assert result.exit_code == 0
            assert "konservita" in result.output or "saved" in result.output

    def test_aldoni_missing_provider(self):
        """Test aldoni without provider argument."""
        result = runner.invoke(app, ["agordi", "aldoni"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestVidiCommand:
    """Tests for `agordi vidi`."""

    def test_vidi_shows_help(self):
        """Test vidi subcommand shows help."""
        result = runner.invoke(app, ["agordi", "vidi", "--help"])
        assert result.exit_code == 0
        assert "vidi" in result.output.lower()

    @patch("A_agento.agordo_crud.get_api_key")
    @patch("A_agento.data.provider_config.get_provider_config")
    def test_vidi_existing(self, mock_get_cfg, mock_get_key):
        """Test viewing an existing provider."""
        mock_get_cfg.return_value = {
            "provider": "openai",
            "profile": "default",
            "modelo": "gpt-4",
            "base_url": "https://api.openai.com/v1",
            "noto": "work",
            "prioritato": 0,
            "kreita_je": "2024-01-01T00:00:00",
            "modifita_je": "2024-01-02T00:00:00",
        }
        mock_get_key.return_value = "sk-test123"

        result = runner.invoke(app, ["agordi", "vidi", "openai"])
        assert result.exit_code == 0
        assert "openai" in result.output.lower()

    @patch("A_agento.data.provider_config.get_provider_config", return_value=None)
    def test_vidi_not_found(self, mock_get_cfg):
        """Test viewing a non-existent provider."""
        result = runner.invoke(app, ["agordi", "vidi", "nonexistent"])
        assert result.exit_code != 0
        assert "ne trovita" in result.output.lower() or "not found" in result.output.lower()


class TestModifiCommand:
    """Tests for `agordi modifi`."""

    def test_modifi_shows_help(self):
        """Test modifi subcommand shows help."""
        result = runner.invoke(app, ["agordi", "modifi", "--help"])
        assert result.exit_code == 0
        assert "modifi" in result.output.lower()

    @patch("A_agento.data.provider_config.get_provider_config")
    @patch("A_agento.agordo_crud.save_provider_config")
    def test_modifi_not_found(self, mock_save_cfg, mock_get_cfg):
        """Test modifying a non-existent provider."""
        mock_get_cfg.return_value = None
        result = runner.invoke(app, ["agordi", "modifi", "nonexistent"])
        assert result.exit_code != 0

    @patch("A_agento.agordo_crud._find_config")
    @patch("A_agento.agordo_crud.save_provider_config")
    def test_modifi_update_base_url(self, mock_save_cfg, mock_find):
        """Test modifying base URL of an existing provider."""
        mock_find.return_value = {
            "provider": "openai",
            "profile": "default",
            "modelo": "gpt-4",
            "base_url": "https://old.endpoint/v1",
            "noto": "",
            "prioritato": 0,
        }

        result = runner.invoke(
            app,
            ["agordi", "modifi", "openai", "--base-url", "https://new.endpoint/v1"],
        )
        assert result.exit_code == 0


class TestForigiCommand:
    """Tests for `agordi forigi`."""

    def test_forigi_shows_help(self):
        """Test forigi subcommand shows help."""
        result = runner.invoke(app, ["agordi", "forigi", "--help"])
        assert result.exit_code == 0
        assert "forigi" in result.output.lower()

    def test_forigi_not_found(self):
        """Test deleting a non-existent provider."""
        result = runner.invoke(app, ["agordi", "forigi", "nonexistent"])
        assert result.exit_code == 0
        assert "ne trovita" in result.output.lower() or "not found" in result.output.lower()

    @patch("A_agento.agordo_crud._delete_provider_config", return_value=True)
    @patch("A_agento.agordo_crud._find_config")
    def test_forigi_with_yes(
        self, mock_find, mock_del
    ):
        """Test deleting a provider with -y flag."""
        mock_find.return_value = {
            "provider": "openai",
            "profile": "default",
        }

        result = runner.invoke(
            app,
            ["agordi", "forigi", "openai", "-y"],
        )
        assert result.exit_code == 0


class TestDeprecatedAliases:
    """Tests for deprecated slosilo/sxlosilo aliases."""

    def test_slosilo_deprecated_works(self):
        """Test slosilo still works (calls aldoni under the hood)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"):
            result = runner.invoke(
                app,
                ["agordi", "slosilo", "openai", "--key", "test"],
            )
            assert result.exit_code == 0

    def test_sxlosilo_deprecated_works(self):
        """Test sxlosilo still works (calls aldoni under the hood)."""
        with patch("A_agento.agordo.save_api_key", return_value=True), \
             patch("A_agento.agordo.save_provider_config"):
            result = runner.invoke(
                app,
                ["agordi", "sxlosilo", "openai", "--key", "test"],
            )
            assert result.exit_code == 0


class TestLsCommand:
    """Tests for `agordi ls`."""

    def test_ls_shows_help(self):
        """Test ls subcommand shows help."""
        result = runner.invoke(app, ["agordi", "ls", "--help"])
        assert result.exit_code == 0
        assert "ls" in result.output.lower()

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.provider_state.get_fallback_order")
    def test_ls_no_configs(self, mock_order, mock_list):
        """Test ls when no providers configured."""
        mock_order.return_value = []
        mock_list.return_value = []

        result = runner.invoke(app, ["agordi", "ls"])
        assert result.exit_code == 0
        assert "Neniuj" in result.output or "No" in result.output

    @patch("A_agento.agordo.list_provider_configs")
    @patch("A_agento.provider_state.get_fallback_order")
    def test_ls_with_configs(self, mock_order, mock_list):
        """Test ls with configured providers."""
        mock_order.return_value = ["openai"]
        mock_list.return_value = [
            {
                "provider": "openai",
                "profile": "default",
                "modelo": "gpt-4",
                "base_url": "",
                "noto": "",
                "prioritato": 0,
            }
        ]

        result = runner.invoke(app, ["agordi", "ls"])
        assert result.exit_code == 0


class TestTestiCommand:
    """Tests for `agordi testi`."""

    def test_testi_shows_help(self):
        """Test testi subcommand shows help."""
        result = runner.invoke(app, ["agordi", "testi", "--help"])
        assert result.exit_code == 0
        assert "testi" in result.output.lower()

    @patch("A_agento.agordo.get_provider")
    def test_testi_success(self, mock_get_provider):
        """Test successful provider test."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.generate.return_value = " OK "
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["agordi", "testi", "--provizanto", "openai"])
        assert result.exit_code == 0
        assert "sukcese" in result.output or "successfully" in result.output

    @patch("A_agento.agordo.get_provider")
    def test_testi_unexpected_response(self, mock_get_provider):
        """Test provider returns unexpected response."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.generate.return_value = "Hello world"
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["agordi", "testi", "--provizanto", "openai"])
        assert result.exit_code == 0

    @patch("A_agento.agordo.get_provider")
    def test_testi_error(self, mock_get_provider):
        """Test provider raises error."""
        mock_provider = Mock()
        mock_provider.name = "test"
        mock_provider.generate.side_effect = ConnectionError("Connection refused")
        mock_get_provider.return_value = mock_provider

        result = runner.invoke(app, ["agordi", "testi", "--provizanto", "openai"])
        assert result.exit_code != 0
        assert "eraro" in result.output or "error" in result.output


class TestAgordoGroup:
    """Tests for agordi group behavior."""

    def test_agordo_shows_help_without_args(self):
        """Test agordo without args shows help."""
        result = runner.invoke(app, ["agordi"])
        assert result.exit_code != 0

    def test_agordo_help(self):
        """Test agordi --help shows subcommands."""
        result = runner.invoke(app, ["agordi", "--help"])
        assert result.exit_code == 0
        assert "default" in result.output
        assert "aldoni" in result.output
        assert "vidi" in result.output
        assert "modifi" in result.output
        assert "forigi" in result.output
        assert "ls" in result.output
        assert "testi" in result.output
