---
name: pantheon-list
description: This skill should be used when the user asks to "list Pantheon titles", "check build states", "see what's configured in Pantheon", "show Pantheon status", or needs to discover titles for a product and version.
---

# List Pantheon Titles

Discover all titles for a product/version in Pantheon, showing job states, branches, and content directories.

## Prerequisites Check

Before running, verify:
1. Kerberos ticket is valid: `klist -s` (run `kinit` if expired)
2. VPN is connected
3. `SSO_EMAIL` is set in `.env`

## Usage

List all titles:
```bash
pantheon-cli list --version <VERSION>
```

Filter by title substring:
```bash
pantheon-cli list --version 1.9 --title "Customizing"
```

Use a different product:
```bash
pantheon-cli list --version 1.9 --product <product_slug>
```

## Output

The output shows columns: Name, Env, State, Branch, Content Dir.

States: `SUCCESS`, `FAILURE`, `DISABLED`, `BUILDING`, `N/A`.

## Common Patterns

- Check if all preview builds succeeded before publishing
- Find titles with mismatched branches
- Identify disabled jobs that need enabling
