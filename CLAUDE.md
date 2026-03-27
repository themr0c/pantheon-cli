# Pantheon CLI

Tools for automating Red Hat Pantheon documentation publishing operations.

## Prerequisites

- Valid Kerberos ticket: `kinit your-id@REDHAT.COM` (verify with `klist`, lasts ~10 hours)
- Red Hat VPN connection
- Playwright Firefox (installed by `bash scripts/setup.sh`)
- `SSO_EMAIL` set in `.env`

## Commands

### pantheon-cli

| Command | Description |
|---|---|
| `pantheon-cli list --version VERSION` | List titles with job states, branches, content dirs |
| `pantheon-cli update --version VERSION --env ENV --branch BRANCH [--directory DIR] [--enable] [--rebuild] [--exec]` | Update build config (dry-run by default) |
| `pantheon-cli rebuild --version VERSION --env ENV [--enable] [--wait] [--exec]` | Trigger rebuilds |
| `pantheon-cli publish --version VERSION [--rebuild-first] [--wait] [--exec]` | Enable + rebuild stage builds |

### visual-diff

| Command | Description |
|---|---|
| `visual-diff urls --version VERSION` | List stage/preview URLs for titles |
| `visual-diff diff --version VERSION --output DIR` | Generate visual diff report |

## Common Options

| Option | Default | Description |
|---|---|---|
| `--product` | `red_hat_developer_hub` | Pantheon product slug |
| `--version` | (required) | Product version (e.g., 1.9, 1.10) |
| `--env` | `preview` | Environment: `preview` or `stage` |
| `--title` | all | Substring filter (repeatable, OR logic) |
| `--exec` | off | Execute changes (default is dry-run) |
| `--fresh` | off | Clear browser session, re-authenticate |
| `--email` | from `SSO_EMAIL` | SSO email override |

## Key Behavior

- **Dry-run by default**: All write operations show a plan without `--exec`. Always review before executing.
- **Browser-based**: Uses Playwright Firefox (headed, not headless) for Kerberos SPNEGO auth.
- **Session persistence**: Browser session cached at `/tmp/pantheon-session/`. Use `--fresh` to clear.

## API Gotchas

- Update API expects **snake_case** (`content_directory`, `content_type`), but GET responses use **camelCase** (`contentDirectory`, `contentType`).
- A TrustArc cookie overlay can block UI interactions — the script removes it automatically.
- After config updates, GET may return stale data for a few seconds.

For full architecture details, see `docs/pantheon-reference.md`.
