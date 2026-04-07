---
name: pantheon-update
description: This skill should be used when the user asks to "update Pantheon build config", "change branch in Pantheon", "change content directory", "enable Pantheon jobs", "update build configuration", or needs to modify build settings for titles.
---

# Update Pantheon Build Configuration

Change build configuration (branch, content directory) for titles in Pantheon.

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

### Dry-run (default)

Always start with a dry-run to review planned changes:
```bash
pantheon-cli update --version <VERSION> --env <ENV> --branch <BRANCH>
```

### Execute changes

After reviewing the dry-run output:
```bash
pantheon-cli update --version <VERSION> --env <ENV> --branch <BRANCH> --exec
```

### Options

- `--branch BRANCH` — Target git branch
- `--directory DIR` — Content directory path
- `--enable` — Enable disabled jobs
- `--rebuild` — Trigger rebuild after update
- `--title FILTER` — Filter to specific titles (repeatable)

### Examples

Update all preview builds to a new branch:
```bash
pantheon-cli update --version 1.9 --env preview --branch release-1.10
```

Update a single title with all options:
```bash
pantheon-cli update --version 1.9 --title "Customizing" --env preview \
  --branch release-1.10 --directory titles/configure_customizing-rhdh \
  --enable --rebuild --exec
```

## Safety

- Always review the dry-run output before using `--exec`
- The tool shows current vs new values for each change
- Changes are applied one title at a time with progress reporting
