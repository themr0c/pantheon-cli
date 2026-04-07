---
name: pantheon-publish
description: This skill should be used when the user asks to "publish to stage", "publish documentation", "enable stage builds", "publish Pantheon release", or needs to enable and rebuild stage environment for a release.
---

# Publish to Stage

Enable and rebuild stage builds for a documentation release in Pantheon.

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

### Dry-run — show disabled stage jobs

```bash
pantheon-cli publish --version <VERSION>
```

### Enable all stage jobs

```bash
pantheon-cli publish --version <VERSION> --exec
```

### Enable and rebuild

```bash
pantheon-cli publish --version <VERSION> --exec --rebuild-first --wait
```

## Typical Publishing Workflow

1. Verify preview builds are all SUCCESS: `pantheon-cli list --version <V>`
2. Review what will be published: `pantheon-cli publish --version <V>`
3. Enable and rebuild: `pantheon-cli publish --version <V> --exec --rebuild-first --wait`
4. Verify stage builds: `pantheon-cli list --version <V> --env stage`
