# Distributable Claude Code Plugin — Design Spec

**Date**: 2026-04-07
**Status**: Draft

## Problem

pantheon-cli is a working Claude Code plugin but requires cloning the git repository to use it. Teammates cannot install it without manual git clone + setup steps. There is no update mechanism.

## Goal

Make pantheon-cli installable with a single command (`claude plugins add --git-url ...`), with automatic setup on first use and automatic updates when changes are pushed to `main`.

## Target Audience

Red Hat documentation team — a handful of people with Kerberos/VPN access who can be onboarded directly.

## Approach

Register the `themr0c/pantheon-cli` GitHub repo as a git URL marketplace. The repo is both the source code and the plugin distribution. Claude Code clones it into its plugin cache, tracks commits, and auto-updates.

## Changes

### 1. Marketplace Manifest

**New file**: `.claude-plugin/marketplace.json`

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

### 2. Auto-setup Hook

**New file**: `hooks/hooks.json`

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

- Fires on session start (not before every tool call — simpler and sufficient)
- `setup.sh` is idempotent — exits quickly (~100ms) after first bootstrap
- `${CLAUDE_PLUGIN_ROOT}` resolves to the cached plugin directory

### 3. Adapt `scripts/setup.sh`

Current script uses `git rev-parse --show-toplevel` and creates a `venv/` inside the repo. This breaks in the plugin cache context (not a git repo, cache can be wiped on update).

Changes:
- **Find itself**: Replace `git rev-parse` with `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"`
- **Venv location**: `~/.cache/pantheon-cli/venv/` (survives plugin cache updates)
- **Symlink**: `~/bin/pantheon-cli` points to `$SCRIPT_DIR/pantheon-cli` (the cached copy)
- **Config location**: `~/.config/pantheon-cli/.env` (user's config, outside the cache)
- **Interactive email prompt**: On first run, if `.env` doesn't exist, prompt for SSO email:

```bash
CONFIG_DIR="$HOME/.config/pantheon-cli"
ENV_FILE="$CONFIG_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  mkdir -p "$CONFIG_DIR"
  read -rp "Enter your Red Hat SSO email: " sso_email
  echo "SSO_EMAIL=$sso_email" > "$ENV_FILE"
fi
```

### 4. Adapt `scripts/pantheon-cli`

The script currently re-execs itself under `venv/` relative to its own location. Change the venv lookup to `~/.cache/pantheon-cli/venv/`.

The `.env` loading also changes from looking at `$REPO_ROOT/.env` to `~/.config/pantheon-cli/.env`.

### 5. Update README

Replace manual setup instructions with:

```
# Install
claude plugins add --git-url https://github.com/themr0c/pantheon-cli.git

# First use auto-bootstraps: venv, deps, Playwright Firefox, SSO email config
# Prerequisites: Python 3.x, Kerberos ticket (kinit), Red Hat VPN
```

## What Stays the Same

- `.claude-plugin/plugin.json` — already correct
- `.claude/settings.json` — pre-allows pantheon-cli, kinit, klist, setup.sh
- All 5 skills (`pantheon-list`, `pantheon-publish`, `pantheon-rebuild`, `pantheon-update`, `splash-configure`)
- Agents (`pantheon-explorer`)
- `CLAUDE.md`

## Update Flow

- User pushes to `main`
- Claude Code detects new commits on next session start, re-caches
- `setup.sh` hook re-runs on next `pantheon-cli` call (idempotent — only re-installs if `requirements.txt` changed)
- Venv at `~/.cache/` survives cache refresh; symlink gets re-pointed to new cache path
- Version field in manifests is informational — git SHA tracks actual state

## Verification

1. From a clean state (no clone), run `claude plugins add --git-url https://github.com/themr0c/pantheon-cli.git`
2. Invoke `/pantheon-list --version 1.9` — should trigger setup.sh, prompt for email, bootstrap venv, then list titles
3. Push a trivial change to `main`, restart Claude — verify plugin updates
4. Run `pantheon-cli list --version 1.9` directly from terminal — should work via `~/bin/` symlink
