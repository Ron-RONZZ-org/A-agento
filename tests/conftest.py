"""Shared fixtures for A-agento tests."""

from __future__ import annotations

import pytest
from unittest.mock import Mock
from pathlib import Path


@pytest.fixture(autouse=True)
def isolate_agento(monkeypatch, tmp_path):
    """Isolate all tests from real config database and keyring.

    Every test automatically writes to tmp_path and uses mock keyring.
    """
    # Isolate database to tmp_path
    from A_agento.data.storage import close_db

    close_db()  # reset singleton before patching
    monkeypatch.setattr("A_agento.data._storage_base.data_dir", lambda: tmp_path)

    # Mock keyring access (real keyring writes are permanent side-effects)
    monkeypatch.setattr("A.core.ai.save_api_key", lambda key, **kw: True)
    monkeypatch.setattr("A.core.ai.get_api_key", lambda **kw: "mock-key")


@pytest.fixture
def mock_provider():
    """A mock LLMProvider that returns canned responses."""
    provider = Mock()
    provider.generate.return_value = "Test summary."
    provider.generate_async.return_value = "Test summary."
    provider.name = "test"
    provider.model = "test-model"
    return provider


@pytest.fixture
def mock_provider_with_json():
    """A mock LLMProvider that returns JSON for action extraction."""
    provider = Mock()
    json_response = """{
        "calendar": {"title": "Meeting", "start": "2024-01-15 15:00", "end": "2024-01-15 16:00", "description": "Team sync"},
        "todo": {"title": "Follow up", "due": "2024-01-16", "priority": "high"},
        "knowledge": {"title": "Project X", "content": "New project details"}
    }"""
    provider.generate.return_value = json_response
    provider.name = "test"
    provider.model = "test-model"
    return provider


@pytest.fixture
def sample_email():
    """A sample email dict for testing."""
    return {
        "uuid": "test-uuid-123",
        "de": "alice@example.com",
        "al": '["bob@example.com"]',
        "subjekto": "Test Meeting",
        "korpo": "Let's meet tomorrow at 3pm.",
        "ricevita_je": "2024-01-14T10:00:00+00:00",
        "legita": 0,
    }


@pytest.fixture
def sample_emails(sample_email):
    """A list of sample emails for testing."""
    return [sample_email]