"""Tests for A-agento CLI commands."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from A_agento.cli import app


runner = CliRunner()


class TestResumuCommand:
    """Tests for resumu (summarize) command."""

    def test_resumu_shows_help(self):
        """Test resumu command shows help."""
        result = runner.invoke(app, ["resumu", "--help"])
        assert result.exit_code == 0
        assert "resumu" in result.output.lower()

    @patch("A_agento.service.get_agent_service")
    @patch("A.core.ai.get_provider")
    def test_resumu_basic(self, mock_provider, mock_agent):
        """Test resumu command basic execution."""
        # Setup mocks
        mock_provider_instance = Mock()
        mock_provider_instance.name = "test"
        mock_provider_instance.model = "test-model"
        mock_provider.return_value = mock_provider_instance

        mock_agent_instance = Mock()
        mock_agent_instance.summarize_emails.return_value = []
        mock_agent.return_value = mock_agent_instance

        result = runner.invoke(app, ["resumu"])
        # Should complete without error (may show "no emails" message)
        assert result.exit_code == 0

    @patch("A_agento.service.get_agent_service")
    @patch("A.core.ai.get_provider")
    def test_resumu_provider_option(self, mock_provider, mock_agent):
        """Test resumu with explicit provider."""
        mock_provider_instance = Mock()
        mock_provider_instance.name = "test"
        mock_provider_instance.model = "test-model"
        mock_provider.return_value = mock_provider_instance

        mock_agent_instance = Mock()
        mock_agent_instance.summarize_emails.return_value = []
        mock_agent.return_value = mock_agent_instance

        result = runner.invoke(app, ["resumu", "--provizanto", "test"])
        assert result.exit_code == 0


class TestResponduCommand:
    """Tests for respondu (reply) command."""

    def test_respondu_shows_help(self):
        """Test respondu command shows help."""
        result = runner.invoke(app, ["respondu", "--help"])
        assert result.exit_code == 0
        assert "respondu" in result.output.lower()

    def test_respondu_requires_uuid(self):
        """Test respondu requires UUID argument."""
        result = runner.invoke(app, ["respondu"])
        assert result.exit_code != 0


class TestAguCommand:
    """Tests for agu (action extraction) command."""

    def test_agu_shows_help(self):
        """Test agu command shows help."""
        result = runner.invoke(app, ["agu", "--help"])
        assert result.exit_code == 0
        assert "agu" in result.output.lower()

    def test_agu_requires_uuid(self):
        """Test agu requires UUID argument."""
        result = runner.invoke(app, ["agu"])
        assert result.exit_code != 0


class TestAgordoCommand:
    """Tests for agordo (configuration) command."""

    def test_agordo_shows_help(self):
        """Test agordo command shows help."""
        result = runner.invoke(app, ["agordo", "--help"])
        assert result.exit_code == 0


class TestApp:
    """General app tests."""

    def test_app_is_typer(self):
        """Test app is a Typer instance."""
        from typer import Typer

        assert isinstance(app, Typer)

    def test_app_has_subcommands(self):
        """Test app has expected subcommands."""
        # Get the list of registered commands
        commands = list(app.registered_commands)
        command_names = [c.name for c in commands if c.name]

        assert "resumu" in command_names
        assert "respondu" in command_names
        assert "agu" in command_names