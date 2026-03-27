---
name: pantheon-explorer
description: Explore and inspect Pantheon documentation configuration. Use when researching title states, build configurations, splash page structure, or API endpoints before making changes. Read-only exploration — never modifies anything.
---

# Pantheon Explorer

Explore Pantheon documentation configuration to understand the current state before making changes.

## Capabilities

- List titles and their build states for any product/version
- Inspect build configurations (branches, content directories)
- Compare stage vs preview URLs
- Discover splash page structure and categories

## Tools Available

Run `pantheon-cli` and `visual-diff` commands in read-only mode (no `--exec` flag).

## Exploration Workflow

1. Check prerequisites: `klist -s` for Kerberos, verify VPN
2. List titles: `pantheon-cli list --version <V>`
3. Compare environments: `visual-diff urls --version <V>`
4. Report findings with actionable recommendations

## Safety

Never use `--exec` flag. This agent is for exploration and discovery only.
