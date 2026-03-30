"""Unit tests for the Reef cookie auth layer in scripts/pantheon-cli."""
import importlib.machinery
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
    script_path = repo_root / "scripts" / "pantheon-cli"
    loader = importlib.machinery.SourceFileLoader("pantheon_cli", str(script_path))
    spec = importlib.util.spec_from_loader("pantheon_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_load_reef_cookies_missing(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        assert cli._load_reef_cookies() is None
    finally:
        cli.REEF_COOKIE_FILE = original


def test_load_reef_cookies_expired(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    cookie_file.write_text(json.dumps({"pantheon-auth": "abc"}))
    old_time = time.time() - 9 * 3600
    os.utime(cookie_file, (old_time, old_time))
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        assert cli._load_reef_cookies() is None
    finally:
        cli.REEF_COOKIE_FILE = original


def test_load_reef_cookies_valid(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    cookies = {"pantheon-auth": "abc", "other": "xyz"}
    cookie_file.write_text(json.dumps(cookies))
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        assert cli._load_reef_cookies() == cookies
    finally:
        cli.REEF_COOKIE_FILE = original


def test_save_reef_cookies_writes_file(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    cookies = {"pantheon-auth": "abc"}
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        cli._save_reef_cookies(cookies)
        assert cookie_file.exists()
        assert json.loads(cookie_file.read_text()) == cookies
    finally:
        cli.REEF_COOKIE_FILE = original


def test_save_reef_cookies_permissions(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        cli._save_reef_cookies({"k": "v"})
        assert oct(cookie_file.stat().st_mode).endswith("600")
    finally:
        cli.REEF_COOKIE_FILE = original


def test_build_reef_session_sets_cookies(cli):
    cookies = {"pantheon-auth": "token123", "session": "sess456"}
    session = cli._build_reef_session(cookies)
    assert session.verify is False
    assert session.cookies.get("pantheon-auth") == "token123"
    assert session.cookies.get("session") == "sess456"
