# Design: Cookie-based Reef API auth for pantheon-cli

**Date:** 2026-03-30
**Status:** Approved

## Goal

Replace Playwright-based browser XHR calls for Reef API operations with direct `requests` HTTP calls. Auth uses the same cookie-extraction pattern already in use for splash commands: Playwright Firefox (headless) handles Kerberos SPNEGO login, cookies are extracted and cached, then all API calls are made via `requests`. Playwright is kept only for the auth step, not for API calls.

## Background

`scripts/pantheon-cli` currently launches a headless Playwright Firefox instance for every Reef command (`list`, `update`, `rebuild`, `publish`). All Reef API calls are made via `page.evaluate()` XHR from inside the browser. Write operations (`updateTitleEnvBuildConfig`, `toggleJenkinsJob`, `startJenkinsJob`) go through Angular's `reefService` injected into the Pantheon page — because that service handles CSRF tokens automatically.

The splash commands already use a better pattern: Playwright only for login + cookie extraction, then `requests` for all API calls. This design applies that same pattern to Reef commands.

Whether the Reef write operations work as plain REST calls (without Angular's CSRF handling) is unknown and will be discovered during implementation.

## Phase 1: Discovery

A one-time dev script (`scripts/discover-reef-api`) will:

1. Launch Playwright Firefox with `page.on("request", ...)` network interception
2. Authenticate via the existing Kerberos SPNEGO login flow
3. Call each Angular write operation once with real data
4. Log every outbound request to `reef.corp.redhat.com`: method, URL, headers, request body
5. Exit without making changes (unless `--exec` is passed)

This reveals the actual REST paths, HTTP methods, and whether CSRF tokens appear in headers. If CSRF tokens are present, a preflight GET to extract the token will be added before each write. The script is discarded after migration is complete.

## Phase 2: Auth layer

**New `get_reef_session()` function** — mirrors existing `get_splash_session()`:
- Load `~/.cache/pantheon-reef-cookies.json` if present and < 8 hours old
- Verify with a cheap GET to the Reef API
- If expired or missing: call `_authenticate_and_extract_reef_cookies(args)` — same flow as `_authenticate_and_extract_cookies()` for splash:
  - Launch Playwright Firefox headless with Kerberos SPNEGO prefs
  - Call `login_and_wait()` (existing function, reused as-is)
  - Extract all cookies, save to `~/.cache/pantheon-reef-cookies.json` (mode 0600)
  - Close browser
  - Falls back to headed mode if headless Kerberos fails (existing fallback pattern)

**`--fresh` on Reef commands**: deletes `~/.cache/pantheon-reef-cookies.json`, then re-authenticates automatically (same as splash `--fresh` behaviour).

**`--email` flag**: still used by the Playwright login flow (passed to `login_and_wait()`), same as before.

**No new dependencies.** `browser_cookie3` is not used.

## Phase 3: API layer

Replace all Playwright-based API calls with direct `requests` calls.

**`reef_get(page, endpoint)` → `reef_get(session, endpoint)`**
Implementation changes from `page.evaluate()` XHR to `session.get(f"{REEF_API}/{endpoint}")`. Signature change is internal only.

**Write operations** — exact endpoints and payloads determined by the discovery script. Expected shape based on Angular service names:

| Angular call | Expected HTTP | Expected path |
| --- | --- | --- |
| `updateTitleEnvBuildConfig` | PUT or POST | `/api/lightblue/update_title_build_config` |
| `toggleJenkinsJob(name, disabled)` | POST | `/api/jenkins/toggle_job` or similar |
| `startJenkinsJob({jobName})` | POST | `/api/jenkins/start_job` or similar |

If discovery reveals CSRF tokens, add a `_get_csrf_token(session)` helper that fetches a page/endpoint to extract the token before each write.

## Command changes

| Command | Change |
| --- | --- |
| `list` | Remove `open_pantheon()`, use `get_reef_session()` |
| `update` | Remove `open_pantheon()`, use `get_reef_session()` |
| `rebuild` | Remove `open_pantheon()`, use `get_reef_session()` |
| `publish` | Remove `open_pantheon()`, use `get_reef_session()` |
| `splash-export` | No change |
| `splash-configure` | No change |

`open_pantheon()` is removed entirely once all Reef commands are migrated.

## Risks

- **Write endpoints need CSRF tokens**: mitigated by preflight GET to extract token
- **Write endpoints don't exist as plain REST**: if true, fall back to keeping `page.evaluate()` XHR for write operations while using `requests` for reads
