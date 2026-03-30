# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Pantheon CLI

Tools for automating Red Hat Pantheon documentation publishing operations.

## Prerequisites

- Valid Kerberos ticket: `kinit your-id@REDHAT.COM` (verify with `klist`, lasts ~10 hours)
- Red Hat VPN connection
- Playwright Firefox (installed by `bash scripts/setup.sh`)
- `SSO_EMAIL` set in `.env`

## Development Setup

```bash
bash scripts/setup.sh   # create venv, install deps, symlink ~/bin/pantheon-cli
```

The script auto-creates `venv/` and symlinks `scripts/pantheon-cli` to `~/bin/pantheon-cli`. The script re-execs itself under the venv python if not already running from it — no manual activation needed.

To run directly without installing:

```bash
./scripts/pantheon-cli --help
```

## Commands

| Command | Description |
| --- | --- |
| `pantheon-cli list --version VERSION` | List titles with job states, branches, content dirs |
| `pantheon-cli update --version VERSION --env ENV --branch BRANCH [--directory DIR] [--enable] [--rebuild] [--exec]` | Update build config (dry-run by default) |
| `pantheon-cli rebuild --version VERSION --env ENV [--enable] [--wait] [--exec]` | Trigger rebuilds |
| `pantheon-cli publish --version VERSION [--rebuild-first] [--wait] [--exec]` | Enable + rebuild stage builds |
| `pantheon-cli splash-export --version VERSION --env ENV [-o FILE]` | Export splash page config to YAML |
| `pantheon-cli splash-configure --version VERSION --env ENV -c FILE [--exec]` | Apply YAML splash page config (dry-run by default) |

## Common Options

| Option | Default | Description |
| --- | --- | --- |
| `--product` | `red_hat_developer_hub` | Pantheon product slug |
| `--version` | (required) | Product version (e.g., 1.9, 1.10) |
| `--env` | `preview` | Environment: `preview` or `stage` |
| `--title` | all | Substring filter (repeatable, OR logic) |
| `--exec` | off | Execute changes (default is dry-run) |
| `--fresh` | off | Clear browser session, re-authenticate |
| `--email` | from `SSO_EMAIL` | SSO email override |

## Architecture

All logic lives in the single script `scripts/pantheon-cli`. There are no modules or packages.

**Two authentication layers:**

- **Reef API commands** (`list`, `update`, `rebuild`, `publish`): Authenticate using Playwright Firefox headless with Kerberos SPNEGO. Cookies are extracted and cached to `~/.cache/pantheon-reef-cookies.json` (8-hour TTL). All Reef API calls are then made via `requests` using those cookies — no XHR or Angular service calls.

- **Splash commands** (`splash-export`, `splash-configure`): Same Playwright auth flow, cookies cached to `~/.cache/pantheon-splash-cookies.json`. DSPM API calls via `requests`.

Both auth layers use the headless→headed fallback pattern and the `--fresh` flag to force re-authentication.

**Reef API** is the internal Jenkins/build orchestration service at `reef.corp.redhat.com`. Build operations (`toggleJenkinsJob`, `startJenkinsJob`, `updateTitleEnvBuildConfig`) are invoked via Angular's `reefService` injected into the page — not as direct HTTP calls — because that service handles CSRF tokens transparently.

**DSPM** is a separate Drupal 10 service managing splash pages, unrelated to Reef. Its form HTML must be parsed with regex (no JSON API) to extract category/title structure and form tokens for POST operations.

## Key Behavior

- **Dry-run by default**: All write operations show a plan without `--exec`. Always review before executing.
- **Session persistence**: `~/.cache/pantheon-reef-cookies.json` (Reef) and `~/.cache/pantheon-splash-cookies.json` (splash). Use `--fresh` to clear and re-authenticate.
- **TrustArc consent**: Always clicks "Agree and proceed" — never just removes the overlay element.

## API Gotchas

- Update API expects **snake_case** (`content_directory`, `content_type`), but GET responses use **camelCase** (`contentDirectory`, `contentType`).
- After config updates, GET may return stale data for a few seconds.
- Splash page category/title structure is parsed from Drupal form HTML field names (pattern: `categories[{uuid}][title][depth]`), not from a JSON API.

For full API details, see [docs/pantheon-reference.md](docs/pantheon-reference.md) and [docs/splash-page-api.md](docs/splash-page-api.md).
