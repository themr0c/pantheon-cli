---
name: pantheon-list
description: This skill should be used when the user asks to "list Pantheon titles", "check build states", "see what's configured in Pantheon", "show Pantheon status", or needs to discover titles for a product and version.
---

# List Pantheon Titles

Discover all titles for a product/version in Pantheon, showing job states, branches, and content directories.

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
