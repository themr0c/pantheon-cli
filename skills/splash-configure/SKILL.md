---
name: splash-configure
description: This skill should be used when the user asks to "configure a splash page", "export splash page", "copy splash page config", "set up splash page categories", "manage splash page", or mentions splash page configuration for Pantheon documentation products.
---

# Splash Page Configuration

Manage Pantheon splash page category structure and title ordering using YAML configuration files.

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

## Overview

Splash pages in Pantheon organize documentation titles into categories (e.g., "Get started", "Install", "Configure"). The splash page is managed by the DXP DSPM service (Drupal 10), not the Reef API. These commands automate the manual process of organizing titles in the Pantheon splash page manager UI.

## Commands

### Export current splash page to YAML

```bash
pantheon-cli splash-export --version 1.9 --env stage -o splash-page.yaml
```

Export the current splash page configuration (categories and title ordering) as a YAML file. Use this to:
- Capture the current configuration as a baseline
- Create a template for configuring a new version

### Apply YAML configuration to a splash page

```bash
# Dry-run first (default)
pantheon-cli splash-configure --version 1.10 --env stage -c splash-page.yaml

# Execute changes
pantheon-cli splash-configure --version 1.10 --env stage -c splash-page.yaml --exec
```

Compare the desired configuration (from YAML) against the current splash page and apply changes. Always configure **Stage first**, then promote to Production.

## YAML Configuration Format

```yaml
product: red_hat_developer_hub
version: "1.9"
environment: stage
categories:
  - name: "Discover"
    titles:
      - "About Red Hat Developer Hub"
  - name: "Get started"
    titles:
      - "Setting up and configuring your first Red Hat Developer Hub instance"
      - "Navigate Red Hat Developer Hub on your first day"
  - name: "Install"
    titles:
      - "Installing Red Hat Developer Hub on OpenShift Container Platform"
      - "Installing Red Hat Developer Hub on Amazon Elastic Kubernetes Service (EKS)"
```

## Typical Workflow

1. **Export** the configured splash page (e.g., 1.9/stage):
   ```bash
   pantheon-cli splash-export --version 1.9 --env stage -o splash-page.yaml
   ```

2. **Review/edit** the YAML file if needed (add/remove titles for new version)

3. **Dry-run** against the target version:
   ```bash
   pantheon-cli splash-configure --version 1.10 --env stage -c splash-page.yaml
   ```

4. **Apply** changes:
   ```bash
   pantheon-cli splash-configure --version 1.10 --env stage -c splash-page.yaml --exec
   ```

5. **Verify** the result by exporting the configured page:
   ```bash
   pantheon-cli splash-export --version 1.10 --env stage
   ```

6. **Promote** to Production via the Pantheon UI (Promote to Production button)

## Safety

- Always configure **Stage** before Production
- Always dry-run first (omit `--exec`) to review changes
- Never modify 1.9/stage directly — it is the live/production configuration
- Use 1.10/stage for testing (not yet published)
- The YAML config file should live in the content repository for version control

## Architecture

Splash pages are managed by the DXP DSPM (Docs 2.0 Splash Page Manager), a Drupal 10 application. Pantheon embeds it via an iframe. The splash commands interact with the DSPM form through Playwright, navigating through Pantheon for authentication. See `docs/splash-page-api.md` for full API reference.
