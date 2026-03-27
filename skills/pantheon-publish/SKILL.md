---
name: pantheon-publish
description: This skill should be used when the user asks to "publish to stage", "publish documentation", "enable stage builds", "publish Pantheon release", or needs to enable and rebuild stage environment for a release.
---

# Publish to Stage

Enable and rebuild stage builds for a documentation release in Pantheon.

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
5. Visual comparison: `visual-diff diff --version <V>`
