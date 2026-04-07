---
name: pantheon-rebuild
description: This skill should be used when the user asks to "rebuild Pantheon titles", "trigger Jenkins builds", "rebuild documentation", "enable and rebuild", or needs to trigger builds for Pantheon titles.
---

# Trigger Pantheon Rebuilds

Trigger Jenkins builds for titles in Pantheon, optionally enabling disabled jobs first.

## First Use / Defaults

Before running the command, check for stored defaults:

1. Read `~/.config/pantheon-cli/.env` for `PRODUCT` and `VERSION` values
2. If `PRODUCT` is not set:
   - Propose `red_hat_developer_hub` as the default
   - Ask the user to confirm or enter a different product slug
   - Offer to save it: append `PRODUCT=<value>` to `~/.config/pantheon-cli/.env`
3. Detect the latest GA version (fast, no auth needed):
   ```bash
   pantheon-cli versions --product <PRODUCT>
   ```
   This outputs `latest-ga: <version>` (e.g., `latest-ga: 1.9`).
4. If `VERSION` is not set, ask the user:
   - Propose the detected GA version as the default
   - Also accept any other version the user types
   - Offer to save it: append `VERSION=<value>` to `~/.config/pantheon-cli/.env`
5. If both defaults exist, show them and proceed. The user can override with `--product` or `--version` flags.

## Prerequisites Check

Before running, verify:
1. Kerberos ticket is valid: `klist -s`
2. VPN is connected

## Usage

### Dry-run

```bash
pantheon-cli rebuild --version <VERSION> --env <ENV>
```

### Execute

```bash
pantheon-cli rebuild --version <VERSION> --env <ENV> --exec
```

### Options

- `--enable` — Enable disabled jobs before rebuilding
- `--wait` — Wait for builds to complete
- `--timeout N` — Max seconds to wait (default: 300)
- `--title FILTER` — Filter to specific titles

### Examples

Enable and rebuild all preview titles:
```bash
pantheon-cli rebuild --version 1.9 --env preview --enable --exec
```

Rebuild one title and wait:
```bash
pantheon-cli rebuild --version 1.9 --title "About" --env preview --exec --wait
```

Rebuild with custom timeout:
```bash
pantheon-cli rebuild --version 1.9 --env preview --exec --wait --timeout 600
```

## Build States

After triggering, monitor states: `BUILDING` → `SUCCESS` or `FAILURE`. Use `--wait` for automatic monitoring.
