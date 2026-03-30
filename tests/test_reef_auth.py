# tests/test_reef_auth.py
"""Unit tests for the Reef cookie auth layer in scripts/pantheon-cli."""
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def cli():
    """Load scripts/pantheon-cli as a module (runs under venv, so imports work)."""
    repo_root = Path(__file__).parent.parent
    spec = importlib.util.spec_from_file_location(
        "pantheon_cli", repo_root / "scripts" / "pantheon-cli"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
