---
name: pantheon-update
description: This skill should be used when the user asks to "update Pantheon build config", "change branch in Pantheon", "change content directory", "enable Pantheon jobs", "update build configuration", or needs to modify build settings for titles.
---

# Update Pantheon Build Configuration

Change build configuration (branch, content directory) for titles in Pantheon.

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
