#!/usr/bin/env bash
set -euo pipefail

# Locate the repo/plugin root relative to this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Stable locations outside plugin cache
VENV_DIR="$HOME/.cache/pantheon-cli/venv"
CONFIG_DIR="$HOME/.config/pantheon-cli"
ENV_FILE="$CONFIG_DIR/.env"
REQ_FILE="$PLUGIN_ROOT/requirements.txt"

# Create/update venv if needed
if [[ ! -f "$VENV_DIR/bin/activate" ]] || [[ "$REQ_FILE" -nt "$VENV_DIR/bin/activate" ]]; then
  echo "Setting up pantheon-cli environment..."
  mkdir -p "$(dirname "$VENV_DIR")"
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q -r "$REQ_FILE"
  touch "$VENV_DIR/bin/activate"
fi

# Install Playwright Firefox if needed
if ! "$VENV_DIR/bin/python" -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
  echo "Installing Playwright Firefox browser..."
  "$VENV_DIR/bin/playwright" install firefox
fi

# Create ~/bin symlink
mkdir -p ~/bin
ln -sf "$PLUGIN_ROOT/scripts/pantheon-cli" ~/bin/pantheon-cli

# Ensure ~/bin is in PATH
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
  if [[ -f "$HOME/.bashrc" ]]; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/bin:$PATH"
  else
    echo "WARNING: ~/bin is not in PATH. Add to your shell profile:" >&2
    echo "  export PATH=\"\$HOME/bin:\$PATH\"" >&2
  fi
fi

# First-run config: prompt for SSO email
if [[ ! -f "$ENV_FILE" ]]; then
  mkdir -p "$CONFIG_DIR"
  read -rp "Enter your Red Hat SSO email: " sso_email
  echo "SSO_EMAIL=$sso_email" > "$ENV_FILE"
  echo "Config saved to $ENV_FILE"
fi

# Source config
# shellcheck disable=SC1090
source "$ENV_FILE"

[[ -z "${SSO_EMAIL:-}" ]] && echo "WARNING: SSO_EMAIL not set in $ENV_FILE" >&2

echo "pantheon-cli: ready."
