# Pantheon CLI

CLI tools for automating Red Hat Pantheon documentation publishing operations. Includes `pantheon-cli` for managing build configurations, triggering rebuilds, and publishing releases, and `visual-diff` for comparing stage vs preview builds.

Repository: <https://github.com/themr0c/pantheon-cli>

## Prerequisites

- **Kerberos ticket** -- Run `kinit` before using the CLI. Verify with `klist`.
- **Red Hat VPN** -- Required for access to `pantheon.cee.redhat.com` and `reef.corp.redhat.com`.
- **Playwright Firefox** -- Installed automatically by `setup.sh`.

## Setup

```bash
git clone git@github.com:themr0c/pantheon-cli.git
cd pantheon-cli
cp .env.example .env
# Edit .env and set SSO_EMAIL to your Red Hat SSO email
bash scripts/setup.sh
```

## Commands

### pantheon-cli

| Command | Description |
|---|---|
| `pantheon-cli list --version 1.9` | List titles with job states, branches, content dirs |
| `pantheon-cli update --version 1.9 --env preview --branch BRANCH [--directory DIR] [--enable] [--rebuild] [--exec]` | Update build config (dry-run by default) |
| `pantheon-cli rebuild --version 1.9 --env preview [--enable] [--wait] [--exec]` | Trigger rebuilds |
| `pantheon-cli publish --version 1.9 [--rebuild-first] [--wait] [--exec]` | Enable + rebuild stage builds |

### visual-diff

| Command | Description |
|---|---|
| `visual-diff urls --version 1.9` | List stage/preview URLs for titles |
| `visual-diff diff --version 1.9 --output /tmp/rhdh-1.9-diff/` | Generate visual diff report |

### Common options

| Option | Default | Description |
|---|---|---|
| `--product` | `red_hat_developer_hub` | Pantheon product slug |
| `--title FILTER` | all | Substring filter (repeatable) |
| `--fresh` | off | Clear session and re-authenticate |
| `--email` | from `SSO_EMAIL` | Override SSO_EMAIL from .env |

## Reference

For architecture details, API methods, and known gotchas, see [docs/pantheon-reference.md](docs/pantheon-reference.md).
