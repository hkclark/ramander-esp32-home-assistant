"""Shared fixtures for Remander tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the in-repo custom integration in every test."""
    yield


@pytest.fixture
def status_payload() -> dict:
    """A representative /api/status response with HA-integration fields populated."""
    return json.loads((FIXTURES / "status.json").read_text())
