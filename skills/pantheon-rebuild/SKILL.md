---
name: pantheon-rebuild
description: This skill should be used when the user asks to "rebuild Pantheon titles", "trigger Jenkins builds", "rebuild documentation", "enable and rebuild", or needs to trigger builds for Pantheon titles.
---

# Trigger Pantheon Rebuilds

Trigger Jenkins builds for titles in Pantheon, optionally enabling disabled jobs first.

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
