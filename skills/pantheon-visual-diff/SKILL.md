---
name: pantheon-visual-diff
description: This skill should be used when the user asks to "compare stage and preview", "visual diff", "compare documentation builds", "check for differences between environments", "screenshot comparison", or needs to visually compare stage vs preview builds.
---

# Visual Diff Between Environments

Compare stage and preview documentation builds visually using screenshots and pixel-diff overlays.

## Prerequisites Check

Before running, verify:
1. Kerberos ticket is valid: `klist -s`
2. VPN is connected

## Commands

### List URLs

Show stage and preview URLs for all titles:
```bash
visual-diff urls --version <VERSION>
```

Output as JSON:
```bash
visual-diff urls --version <VERSION> --json
```

### Generate Diff Report

Create an HTML report with side-by-side screenshots:
```bash
visual-diff diff --version <VERSION> --output /tmp/rhdh-diff/
```

Diff a single title:
```bash
visual-diff diff --version <VERSION> --title "About" --output /tmp/rhdh-diff/
```

## Output

The report at `<output>/index.html` shows:
- Summary table with status per title (identical, CHANGED, error, skipped)
- Side-by-side screenshots for changed titles
- Diff overlay highlighting pixel differences in red

## Options

- `--headless` — Run browser in headless mode (faster, but may not work with Kerberos)
- `--title FILTER` — Filter to specific titles
- `--fresh` — Clear browser session
