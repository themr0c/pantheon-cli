# Pantheon CLI

CLI tools for automating Red Hat Pantheon documentation publishing operations. Includes `pantheon-cli` for managing build configurations, triggering rebuilds, publishing releases, and managing splash page configurations.

Repository: <https://github.com/themr0c/pantheon-cli>

## Prerequisites

- **Kerberos ticket** -- Run `kinit` before using the CLI. Verify with `klist`.
- **Red Hat VPN** -- Required for access to `pantheon.cee.redhat.com` and `reef.corp.redhat.com`.
- **Playwright Firefox** -- Installed automatically by `setup.sh`.

## Install

### As a Claude Code plugin (recommended)

```bash
claude plugins marketplace add git@github.com:themr0c/pantheon-cli.git
claude plugins install pantheon-cli
```

First use auto-bootstraps: Python venv, dependencies, Playwright Firefox, and SSO email config.

To update the plugin:

```bash
claude plugins marketplace update pantheon-cli
```

### For development

```bash
git clone git@github.com:themr0c/pantheon-cli.git
cd pantheon-cli
bash scripts/setup.sh
```

## Commands

### pantheon-cli

| Command | Description |
|---|---|
| `pantheon-cli versions` | Detect current GA version (fast, no auth needed) |
| `pantheon-cli list --version 1.9` | List titles with job states, branches, content dirs |
| `pantheon-cli update --version 1.9 --env preview --branch BRANCH [--directory DIR] [--enable] [--rebuild] [--exec]` | Update build config (dry-run by default) |
| `pantheon-cli rebuild --version 1.9 --env preview [--enable] [--wait] [--exec]` | Trigger rebuilds |
| `pantheon-cli publish --version 1.9 [--rebuild-first] [--wait] [--exec]` | Enable + rebuild stage builds |
| `pantheon-cli splash-export --version 1.9 --env stage [-o FILE]` | Export splash page config to YAML |
| `pantheon-cli splash-configure --version 1.9 --env stage -c FILE [--exec]` | Apply YAML splash page config (dry-run by default) |

### Common options

| Option | Default | Description |
|---|---|---|
| `--product` | `red_hat_developer_hub` | Pantheon product slug |
| `--title FILTER` | all | Substring filter (repeatable) |
| `--fresh` | off | Clear session and re-authenticate |
| `--email` | from `SSO_EMAIL` | Override SSO_EMAIL from .env |

## Reference

For architecture details, API methods, and known gotchas, see [docs/pantheon-reference.md](docs/pantheon-reference.md) and [docs/splash-page-api.md](docs/splash-page-api.md).
