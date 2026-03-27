#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Create/update venv if needed
if [[ ! -f venv/bin/activate ]] || [[ requirements.txt -nt venv/bin/activate ]]; then
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
  touch venv/bin/activate
fi

# Create ~/bin symlinks
mkdir -p ~/bin
ln -sf "$REPO_ROOT/scripts/pantheon-cli" ~/bin/pantheon-cli
ln -sf "$REPO_ROOT/scripts/visual-diff" ~/bin/visual-diff

# Install Playwright Firefox browser if needed
if ! venv/bin/python -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
  echo "Installing Playwright Firefox browser..."
  venv/bin/playwright install firefox
fi

if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
  if [[ -f "$HOME/.bashrc" ]]; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/bin:$PATH"
  else
    echo "WARNING: ~/bin is not in PATH. Add to your shell profile:" >&2
    echo "  export PATH=\"\$HOME/bin:\$PATH\"" >&2
  fi
fi

# Check .env
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

[[ -z "${SSO_EMAIL:-}" ]] && echo "WARNING: SSO_EMAIL not set in .env" >&2

echo "Setup OK."
