# Distributable Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pantheon-cli installable via `claude plugins add --git-url` with automatic setup and updates.

**Architecture:** The GitHub repo doubles as a Claude Code marketplace. A `marketplace.json` registers the single plugin. A `SessionStart` hook runs `scripts/setup.sh` idempotently. The venv and config live outside the plugin cache so they survive updates.

**Tech Stack:** Bash (setup.sh), Python (pantheon-cli), Claude Code plugin hooks system

---

### Task 1: Add marketplace manifest

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create marketplace.json**

```json
{
  "name": "pantheon-cli",
  "description": "Red Hat Pantheon documentation publishing automation",
  "owner": { "name": "Fabrice Flore-Thébault" },
  "plugins": [
    {
      "name": "pantheon-cli",
      "source": ".",
      "description": "List titles, update build configs, trigger rebuilds, publish releases, manage splash pages",
      "version": "1.0.0"
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add marketplace manifest for plugin distribution"
```

---

### Task 2: Add setup hook

**Files:**
- Create: `hooks/hooks.json`

The hook runs `scripts/setup.sh` on session start. The format follows the Claude Code plugin hooks spec (see `superpowers/5.0.7/hooks/hooks.json` for reference). The hook uses `SessionStart` so setup runs once per session, not before every tool call.

- [ ] **Step 1: Create hooks directory and hooks.json**

```json
{
  "description": "Bootstrap pantheon-cli venv, dependencies, and Playwright Firefox on first use",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh\"",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat: add session-start hook to auto-run setup.sh"
```

---

### Task 3: Adapt setup.sh for plugin cache context

**Files:**
- Modify: `scripts/setup.sh`

The current script uses `git rev-parse --show-toplevel` (fails in plugin cache — not a git repo) and creates venv inside the repo (lost on cache refresh). Adapt to use stable external paths.

- [ ] **Step 1: Rewrite setup.sh**

Replace the entire file with:

```bash
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
```

- [ ] **Step 2: Verify setup.sh works from repo root**

Run from the repo root to confirm it still works for the developer workflow:

```bash
bash scripts/setup.sh
```

Expected: creates venv at `~/.cache/pantheon-cli/venv/`, symlinks `~/bin/pantheon-cli`, sources config from `~/.config/pantheon-cli/.env`. Prints "pantheon-cli: ready."

- [ ] **Step 3: Commit**

```bash
git add scripts/setup.sh
git commit -m "refactor: adapt setup.sh for plugin cache context

Venv moved to ~/.cache/pantheon-cli/venv/ (survives cache refresh).
Config moved to ~/.config/pantheon-cli/.env (prompts on first run).
Uses SCRIPT_DIR instead of git rev-parse (works outside git repos)."
```

---

### Task 4: Adapt pantheon-cli venv re-exec and .env loading

**Files:**
- Modify: `scripts/pantheon-cli` (lines 1-34)

The script currently looks for `venv/` relative to its parent directory and `.env` at repo root. Update both to use the stable external paths.

- [ ] **Step 1: Update venv re-exec block**

Replace lines 12-17:

```python
# Re-exec under the repo venv if not already running from it
_script = Path(__file__).resolve()
_repo_root = _script.parent.parent
_venv_python = _repo_root / 'venv' / 'bin' / 'python'
if _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    os.execv(str(_venv_python), [str(_venv_python), str(_script)] + sys.argv[1:])
```

With:

```python
# Re-exec under the pantheon-cli venv if not already running from it
_script = Path(__file__).resolve()
_venv_python = Path.home() / '.cache' / 'pantheon-cli' / 'venv' / 'bin' / 'python'
if _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    os.execv(str(_venv_python), [str(_venv_python), str(_script)] + sys.argv[1:])
```

- [ ] **Step 2: Update .env loading block**

Replace lines 26-33:

```python
# Load .env from repo root
_env_file = _repo_root / '.env'
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()
```

With:

```python
# Load .env from user config
_env_file = Path.home() / '.config' / 'pantheon-cli' / '.env'
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()
```

- [ ] **Step 3: Remove unused `_repo_root` variable**

After the two changes above, `_repo_root` is no longer used. Remove the line:

```python
_repo_root = _script.parent.parent
```

- [ ] **Step 4: Verify pantheon-cli still works**

```bash
pantheon-cli list --version 1.9
```

Expected: authenticates and lists titles as before. If venv was at the old location, first run `bash scripts/setup.sh` to create it at the new path.

- [ ] **Step 5: Commit**

```bash
git add scripts/pantheon-cli
git commit -m "refactor: use stable venv and config paths in pantheon-cli

Venv: ~/.cache/pantheon-cli/venv/ (was relative venv/)
Config: ~/.config/pantheon-cli/.env (was repo-root .env)"
```

---

### Task 5: Update README with install instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace Setup section**

Replace the current Setup section (lines 14-20):

```markdown
## Setup

```bash
git clone git@github.com:themr0c/pantheon-cli.git
cd pantheon-cli
cp .env.example .env
# Edit .env and set SSO_EMAIL to your Red Hat SSO email
bash scripts/setup.sh
```
```

With:

```markdown
## Install

### As a Claude Code plugin (recommended)

```bash
claude plugins add --git-url https://github.com/themr0c/pantheon-cli.git
```

First use auto-bootstraps: Python venv, dependencies, Playwright Firefox, and SSO email config.

### For development

```bash
git clone git@github.com:themr0c/pantheon-cli.git
cd pantheon-cli
bash scripts/setup.sh
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add plugin install instructions to README"
```

---

### Task 6: End-to-end verification

No files to change — this is a manual verification checklist.

- [ ] **Step 1: Verify setup.sh is idempotent**

Run `bash scripts/setup.sh` twice in a row. Second run should print "pantheon-cli: ready." without reinstalling anything.

- [ ] **Step 2: Verify pantheon-cli works with new paths**

```bash
pantheon-cli list --version 1.9
```

Expected: lists all titles. Cookies still cached at `~/.cache/pantheon-reef-cookies.json`.

- [ ] **Step 3: Verify hook file is valid JSON**

```bash
python3 -c "import json; json.load(open('hooks/hooks.json')); print('OK')"
```

- [ ] **Step 4: Verify marketplace manifest is valid JSON**

```bash
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('OK')"
```

- [ ] **Step 5: Verify plugin structure**

Check that all required plugin files exist:

```bash
ls -la .claude-plugin/plugin.json .claude-plugin/marketplace.json hooks/hooks.json scripts/setup.sh scripts/pantheon-cli
```

- [ ] **Step 6: Test fresh install (optional, requires pushing to GitHub first)**

Push changes to `main`, then from a machine without the repo cloned:

```bash
claude plugins add --git-url https://github.com/themr0c/pantheon-cli.git
```

Then invoke a skill and verify setup.sh runs automatically.
