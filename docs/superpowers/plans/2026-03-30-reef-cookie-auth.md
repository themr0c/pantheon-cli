# Reef Cookie Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Playwright XHR calls for all Reef API operations with direct `requests` calls, using the same cookie-extraction auth pattern already in use for splash commands.

**Architecture:** A discovery script intercepts network requests made by Angular's `reefService` to reveal the actual REST endpoints. Then `scripts/pantheon-cli` is updated to: (1) add a `get_reef_session()` function that uses Playwright Firefox headless only for Kerberos SPNEGO login and cookie extraction, caching the result; (2) replace all `page.evaluate()` XHR calls with direct `requests` calls. `open_pantheon()` is removed.

**Tech Stack:** Python 3, Playwright (Firefox, headless, Kerberos SPNEGO), `requests`, `pytest`

---

## File Map

| File | Action | Purpose |
| --- | --- | --- |
| `scripts/discover-reef-api` | Create (temp) | Intercept Angular reefService network calls, print actual REST endpoints |
| `scripts/pantheon-cli` | Modify | Add reef auth layer, replace XHR with requests, remove `open_pantheon()` |
| `tests/test_reef_auth.py` | Create | Unit tests for cookie load/save/TTL logic |
| `requirements.txt` | Modify | Add `pytest` |

---

## Task 1: Create the discovery script

**Files:**
- Create: `scripts/discover-reef-api`

The discovery script authenticates via the existing Pantheon session, then uses `page.route()` to intercept (but abort) all write requests to `reef.corp.redhat.com` while calling Angular's reefService write operations. This reveals exact REST paths, HTTP methods, and request bodies without actually executing writes.

- [ ] **Step 1: Create `scripts/discover-reef-api`**

```python
#!/usr/bin/env python3
"""Discover Reef API endpoints by intercepting Angular reefService write calls.

Run this once to capture the actual REST endpoints, HTTP methods, and request
bodies used by updateTitleEnvBuildConfig, toggleJenkinsJob, and startJenkinsJob.
Write requests are intercepted and aborted — no changes are made.

Usage:
    scripts/discover-reef-api --version 1.9 --title "My Title Name"
"""

import os
import sys
import json
import time
import importlib.util
import argparse
from pathlib import Path

_script = Path(__file__).resolve()
_repo_root = _script.parent.parent
_venv_python = _repo_root / 'venv' / 'bin' / 'python'
if _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    os.execv(str(_venv_python), [str(_venv_python), str(_script)] + sys.argv[1:])

_env_file = _repo_root / '.env'
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()


def _load_cli():
    spec = importlib.util.spec_from_file_location(
        "pantheon_cli", _repo_root / "scripts" / "pantheon-cli"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True, help="Product version, e.g. 1.9")
    parser.add_argument("--title", required=True, help="Title name substring to match")
    parser.add_argument("--product", default="red_hat_developer_hub")
    parser.add_argument("--env", default="preview")
    parser.add_argument("--email", default=os.environ.get("SSO_EMAIL", ""))
    args = parser.parse_args()

    if not args.email:
        sys.exit("Error: Set SSO_EMAIL in .env or use --email")

    cli = _load_cli()

    from playwright.sync_api import sync_playwright
    SESSION_DIR = str(Path.home() / ".cache" / "pantheon-session")

    intercepted = []

    def intercept_write(route, request):
        """Log write requests and abort them — reads are allowed through."""
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            intercepted.append({
                "method": request.method,
                "url": request.url,
                "post_data": request.post_data,
                "headers": {
                    k: v for k, v in request.headers.items()
                    if k.lower() in ("content-type", "x-csrf-token", "authorization",
                                     "x-xsrf-token", "referer")
                },
            })
            route.abort()
        else:
            route.continue_()

    p = sync_playwright().start()
    browser = p.firefox.launch_persistent_context(
        SESSION_DIR,
        headless=True,
        viewport={"width": 1400, "height": 900},
        ignore_https_errors=True,
        firefox_user_prefs={
            "network.negotiate-auth.trusted-uris": ".redhat.com,.cee.redhat.com",
        },
    )
    page = browser.pages[0] if browser.pages else browser.new_page()

    if not cli.login_and_wait(page, args.email):
        browser.close()
        p.stop()
        sys.exit(1)

    # Navigate to titles page so Angular app and reefService are loaded
    titles_url = f"{cli.PANTHEON_URL}#/titles/{args.product}/{args.version}"
    page.goto(titles_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)
    page.wait_for_selector("[ng-repeat*='title']", timeout=30000)
    time.sleep(2)

    # Find a matching title
    titles = cli.get_titles(page, args.product, args.version)
    matching = [t for t in titles if args.title.lower() in t["name"].lower()]
    if not matching:
        print(f"No title matching '{args.title}' found. Available:")
        for t in titles[:10]:
            print(f"  {t['name']}")
        browser.close()
        p.stop()
        sys.exit(1)

    t = matching[0]
    uuid = t["uuid"]
    job = t.get("jobs", {}).get(args.env, {})
    job_name = job.get("jobName", "")
    config = cli.get_build_config(page, uuid, args.env)
    current_branch = config.get("branch", "main")
    current_dir = config.get("contentDirectory", "")
    content_type = config.get("contentType", "book")

    print(f"\nTitle:   {t['name']}")
    print(f"UUID:    {uuid}")
    print(f"Job:     {job_name}")
    print(f"Branch:  {current_branch}  Dir: {current_dir}")
    print("\n--- Intercepting write operations (aborted, no changes made) ---")

    # Install route interceptor before triggering writes
    page.route("**reef.corp.redhat.com**", intercept_write)

    print("Calling updateTitleEnvBuildConfig...")
    page.evaluate("""([uuid, lang, env, branch, dir, contentType]) => {
        const injector = angular.element(document.body).injector();
        const reef = injector.get('reefService');
        reef.updateTitleEnvBuildConfig(uuid, lang, env, {
            branch: branch,
            content_directory: dir,
            content_type: contentType
        }).catch(() => {});
    }""", [uuid, "en-US", args.env, current_branch, current_dir, content_type])
    time.sleep(2)

    if job_name:
        print("Calling toggleJenkinsJob...")
        page.evaluate("""([jobName]) => {
            const injector = angular.element(document.body).injector();
            const reef = injector.get('reefService');
            try { reef.toggleJenkinsJob(jobName, false); } catch(e) {}
        }""", [job_name])
        time.sleep(2)

        print("Calling startJenkinsJob...")
        page.evaluate("""([jobName]) => {
            const injector = angular.element(document.body).injector();
            const reef = injector.get('reefService');
            try { reef.startJenkinsJob({jobName: jobName}); } catch(e) {}
        }""", [job_name])
        time.sleep(2)
    else:
        print(f"(No job found for env={args.env}, skipping toggle/start)")

    browser.close()
    p.stop()

    print("\n" + "=" * 60)
    print(f"INTERCEPTED {len(intercepted)} WRITE REQUEST(S):")
    print("=" * 60)
    for w in intercepted:
        print(f"\n{w['method']} {w['url']}")
        if w["headers"]:
            print(f"  headers: {json.dumps(w['headers'], indent=4)}")
        if w["post_data"]:
            print(f"  body: {w['post_data'][:2000]}")
    print("\n" + "=" * 60)
    print("Update scripts/pantheon-cli with these endpoints and bodies.")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x scripts/discover-reef-api
```

- [ ] **Step 3: Commit**

```bash
git add scripts/discover-reef-api
git commit -m "feat: add discovery script for Reef API endpoints"
```

---

## Task 2: Run discovery, document findings

**Files:**
- Modify: `docs/superpowers/plans/2026-03-30-reef-cookie-auth.md` (this file — add findings below)

- [ ] **Step 1: Run the discovery script against a real title**

```bash
scripts/discover-reef-api --version 1.9 --title "SOME TITLE NAME"
```

Replace `1.9` and `"SOME TITLE NAME"` with an actual version and a title that has a job configured in the preview env.

- [ ] **Step 2: Record findings here**

After running, paste the output below and use it to fill in Task 6.

```
# Discovery findings (fill in after running):
# updateTitleEnvBuildConfig:
#   METHOD: ???
#   URL: ???
#   body keys: ???
#   CSRF header: yes/no, name: ???
#
# toggleJenkinsJob:
#   METHOD: ???
#   URL: ???
#   body keys: ???
#
# startJenkinsJob:
#   METHOD: ???
#   URL: ???
#   body keys: ???
```

- [ ] **Step 3: Commit findings**

```bash
git add docs/superpowers/plans/2026-03-30-reef-cookie-auth.md
git commit -m "docs: record Reef API endpoint discovery findings"
```

---

## Task 3: Add pytest and test infrastructure

**Files:**
- Modify: `requirements.txt`
- Create: `tests/test_reef_auth.py` (skeleton)

- [ ] **Step 1: Add pytest to requirements.txt**

Append to `requirements.txt`:

```
pytest>=7.0
```

- [ ] **Step 2: Reinstall dependencies**

```bash
venv/bin/pip install -q -r requirements.txt
```

Expected: output includes `Successfully installed pytest-...` (or "already satisfied").

- [ ] **Step 3: Create tests directory and skeleton test file**

```python
# tests/test_reef_auth.py
"""Unit tests for the Reef cookie auth layer in scripts/pantheon-cli."""
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def cli():
    """Load scripts/pantheon-cli as a module (runs under venv, so imports work)."""
    repo_root = Path(__file__).parent.parent
    spec = importlib.util.spec_from_file_location(
        "pantheon_cli", repo_root / "scripts" / "pantheon-cli"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

- [ ] **Step 4: Verify pytest discovers the file**

```bash
venv/bin/pytest tests/test_reef_auth.py --collect-only
```

Expected output includes `<Module test_reef_auth.py>` (no errors, just no tests yet).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/test_reef_auth.py
git commit -m "test: add pytest and test scaffold for reef auth"
```

---

## Task 4: Add reef auth layer to `scripts/pantheon-cli`

**Files:**
- Modify: `scripts/pantheon-cli`
- Modify: `tests/test_reef_auth.py`

Add the reef auth constants and functions immediately after the existing splash constants block (after `SPLASH_COOKIE_FILE`).

- [ ] **Step 1: Write the failing tests first**

Replace the content of `tests/test_reef_auth.py` with:

```python
"""Unit tests for the Reef cookie auth layer in scripts/pantheon-cli."""
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def cli():
    """Load scripts/pantheon-cli as a module (runs under venv, so imports work)."""
    repo_root = Path(__file__).parent.parent
    spec = importlib.util.spec_from_file_location(
        "pantheon_cli", repo_root / "scripts" / "pantheon-cli"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_load_reef_cookies_missing(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        assert cli._load_reef_cookies() is None
    finally:
        cli.REEF_COOKIE_FILE = original


def test_load_reef_cookies_expired(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    cookie_file.write_text(json.dumps({"pantheon-auth": "abc"}))
    old_time = time.time() - 9 * 3600
    os.utime(cookie_file, (old_time, old_time))
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        assert cli._load_reef_cookies() is None
    finally:
        cli.REEF_COOKIE_FILE = original


def test_load_reef_cookies_valid(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    cookies = {"pantheon-auth": "abc", "other": "xyz"}
    cookie_file.write_text(json.dumps(cookies))
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        assert cli._load_reef_cookies() == cookies
    finally:
        cli.REEF_COOKIE_FILE = original


def test_save_reef_cookies_writes_file(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    cookies = {"pantheon-auth": "abc"}
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        cli._save_reef_cookies(cookies)
        assert cookie_file.exists()
        assert json.loads(cookie_file.read_text()) == cookies
    finally:
        cli.REEF_COOKIE_FILE = original


def test_save_reef_cookies_permissions(cli, tmp_path):
    cookie_file = tmp_path / "reef-cookies.json"
    original = cli.REEF_COOKIE_FILE
    cli.REEF_COOKIE_FILE = cookie_file
    try:
        cli._save_reef_cookies({"k": "v"})
        assert oct(cookie_file.stat().st_mode)[-3:] == "600"
    finally:
        cli.REEF_COOKIE_FILE = original


def test_build_reef_session_sets_cookies(cli):
    cookies = {"pantheon-auth": "token123", "session": "sess456"}
    session = cli._build_reef_session(cookies)
    assert session.verify is False
    assert session.cookies.get("pantheon-auth") == "token123"
    assert session.cookies.get("session") == "sess456"
```

- [ ] **Step 2: Run tests — expect failures (functions don't exist yet)**

```bash
venv/bin/pytest tests/test_reef_auth.py -v
```

Expected: `AttributeError: module 'pantheon_cli' has no attribute 'REEF_COOKIE_FILE'` (or similar for each test).

- [ ] **Step 3: Add reef auth constants and functions to `scripts/pantheon-cli`**

Locate the line:
```python
SPLASH_COOKIE_FILE = Path.home() / ".cache" / "pantheon-splash-cookies.json"
```

Add immediately after it:

```python
REEF_SESSION_DIR = str(Path.home() / ".cache" / "pantheon-reef-session")
REEF_COOKIE_FILE = Path.home() / ".cache" / "pantheon-reef-cookies.json"
```

Then locate the section comment `# Subcommand: list` and add the following block immediately before it:

```python
# ---------------------------------------------------------------------------
# Reef cookie auth (mirrors splash auth pattern)
# ---------------------------------------------------------------------------

def _load_reef_cookies():
    """Load cached Reef cookies if they exist and are < 8 hours old."""
    if not REEF_COOKIE_FILE.exists():
        return None
    age = time.time() - REEF_COOKIE_FILE.stat().st_mtime
    if age > 8 * 3600:
        return None
    return json.loads(REEF_COOKIE_FILE.read_text())


def _save_reef_cookies(cookies):
    """Cache Reef cookies to disk."""
    REEF_COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REEF_COOKIE_FILE.write_text(json.dumps(cookies))
    REEF_COOKIE_FILE.chmod(0o600)


def _build_reef_session(cookies):
    """Build a requests.Session with Reef auth cookies."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    s = requests.Session()
    for name, value in cookies.items():
        s.cookies.set(name, value)
    s.verify = False
    return s


def _authenticate_and_extract_reef_cookies(args):
    """Launch Playwright Firefox, login via Kerberos SPNEGO, extract cookies.

    Tries headless first. Falls back to headed if headless SPNEGO fails.
    """
    if args.fresh and os.path.exists(REEF_SESSION_DIR):
        shutil.rmtree(REEF_SESSION_DIR)

    for headless in (True, False):
        p = sync_playwright().start()
        browser = p.firefox.launch_persistent_context(
            REEF_SESSION_DIR,
            headless=headless,
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
            firefox_user_prefs={
                "network.negotiate-auth.trusted-uris": ".redhat.com,.cee.redhat.com",
            },
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            if login_and_wait(page, args.email):
                cookies = _extract_cookies(browser)
                _save_reef_cookies(cookies)
                print(f"Reef session: captured {len(cookies)} cookies.")
                return cookies

            if headless:
                print("Headless auth failed, retrying with headed browser...")
                browser.close()
                p.stop()
                continue
            else:
                sys.exit("ERROR: Authentication failed.")
        except SystemExit:
            raise
        except Exception as e:
            if headless:
                print(f"Headless auth error ({e}), retrying with headed browser...")
                browser.close()
                p.stop()
                continue
            raise
        finally:
            try:
                browser.close()
                p.stop()
            except Exception:
                pass


def get_reef_session(args):
    """Get a requests.Session authenticated for Reef API access.

    Uses cached cookies if available; otherwise launches Playwright for login.
    """
    cookies = _load_reef_cookies()
    if cookies and not args.fresh:
        session = _build_reef_session(cookies)
        try:
            r = session.get(
                f"{REEF_API}/lightblue/get_products", timeout=10
            )
            if r.status_code == 200:
                print("Using cached Reef session.")
                return session
        except Exception:
            pass
        print("Cached Reef session expired, re-authenticating...")

    cookies = _authenticate_and_extract_reef_cookies(args)
    return _build_reef_session(cookies)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
venv/bin/pytest tests/test_reef_auth.py -v
```

Expected:
```
PASSED tests/test_reef_auth.py::test_load_reef_cookies_missing
PASSED tests/test_reef_auth.py::test_load_reef_cookies_expired
PASSED tests/test_reef_auth.py::test_load_reef_cookies_valid
PASSED tests/test_reef_auth.py::test_save_reef_cookies_writes_file
PASSED tests/test_reef_auth.py::test_save_reef_cookies_permissions
PASSED tests/test_reef_auth.py::test_build_reef_session_sets_cookies
6 passed
```

- [ ] **Step 5: Commit**

```bash
git add scripts/pantheon-cli tests/test_reef_auth.py
git commit -m "feat: add reef cookie auth layer (get_reef_session)"
```

---

## Task 5: Replace `reef_get()` and read API functions

**Files:**
- Modify: `scripts/pantheon-cli`

The current `reef_get(page, endpoint)` uses XHR via `page.evaluate()`. Replace with a direct `requests` call.

- [ ] **Step 1: Replace `reef_get` in `scripts/pantheon-cli`**

Find and replace:

```python
def reef_get(page, endpoint):
    """GET request to Reef API via browser XHR."""
    url = f"{REEF_API}/{endpoint}"
    response = page.evaluate("""(url) => {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', url, true);
            xhr.withCredentials = true;
            xhr.onload = () => resolve({status: xhr.status, body: xhr.responseText});
            xhr.onerror = () => reject('XHR error: ' + xhr.statusText);
            xhr.send();
        });
    }""", url)
    if response['status'] != 200:
        raise RuntimeError(
            f"Reef GET {endpoint}: HTTP {response['status']}: "
            f"{response['body'][:200]}"
        )
    return json.loads(response['body'])
```

With:

```python
def reef_get(session, endpoint):
    """GET request to Reef API via requests session."""
    url = f"{REEF_API}/{endpoint}"
    r = session.get(url, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(
            f"Reef GET {endpoint}: HTTP {r.status_code}: {r.text[:200]}"
        )
    return r.json()
```

- [ ] **Step 2: Update `get_titles` and `get_build_config` signatures**

Find:
```python
def get_titles(page, product, version):
    """Get all titles for a product/version."""
    data = reef_get(
        page,
        f"lightblue/get_titles?combineBrewed=false&lang=en-US"
        f"&product={product}&version={version}"
    )
    return data['data']['products'][0]['versions'][0]['titles']


def get_build_config(page, uuid, env="preview"):
    """Get current build config for a title."""
    data = reef_get(
        page,
        f"lightblue/get_title_build_config?uuid={uuid}&lang=en-US&environment={env}"
    )
    return data.get('data', {})
```

Replace with:
```python
def get_titles(session, product, version):
    """Get all titles for a product/version."""
    data = reef_get(
        session,
        f"lightblue/get_titles?combineBrewed=false&lang=en-US"
        f"&product={product}&version={version}"
    )
    return data['data']['products'][0]['versions'][0]['titles']


def get_build_config(session, uuid, env="preview"):
    """Get current build config for a title."""
    data = reef_get(
        session,
        f"lightblue/get_title_build_config?uuid={uuid}&lang=en-US&environment={env}"
    )
    return data.get('data', {})
```

- [ ] **Step 3: Commit**

```bash
git add scripts/pantheon-cli
git commit -m "refactor: replace reef_get XHR with direct requests call"
```

---

## Task 6: Replace write operations

**Files:**
- Modify: `scripts/pantheon-cli`

Replace the three `page.evaluate()` write operations with `requests` calls. The endpoint URLs and body shapes below are derived from the Angular service names and the `reef-publish.py` pattern — **verify against the Task 2 discovery output and update if they differ**.

- [ ] **Step 1: Replace `update_build_config`**

Find:
```python
def update_build_config(page, uuid, env, branch, content_dir, content_type="book"):
```

Replace the entire function:

```python
def update_build_config(session, uuid, env, branch, content_dir, content_type="book"):
    """Update build config via direct Reef API call.

    Endpoint verified via scripts/discover-reef-api — update URL if discovery
    output shows a different path.
    """
    r = session.post(
        f"{REEF_API}/lightblue/update_title_build_config",
        json={
            "uuid": uuid,
            "lang": "en-US",
            "environment": env,
            "branch": branch,
            "content_directory": content_dir,
            "content_type": content_type,
        },
    )
    if not r.ok:
        raise RuntimeError(
            f"Update failed (HTTP {r.status_code}): {r.text[:300]}"
        )
    return r.json()
```

- [ ] **Step 2: Replace `toggle_job`**

Find:
```python
def toggle_job(page, job_name, enable):
```

Replace the entire function:

```python
def toggle_job(session, job_name, enable):
    """Enable or disable a Jenkins job via direct Reef API call.

    disabled=False means enabled. Endpoint verified via scripts/discover-reef-api.
    """
    r = session.post(
        f"{REEF_API}/jenkins/toggle_jenkins_job",
        json={
            "jobName": job_name,
            "disabled": not enable,
        },
    )
    if not r.ok:
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    return {"ok": True}
```

- [ ] **Step 3: Replace `start_build`**

Find:
```python
def start_build(page, job_name):
```

Replace the entire function:

```python
def start_build(session, job_name):
    """Trigger a Jenkins build via direct Reef API call.

    Endpoint verified via scripts/discover-reef-api.
    """
    r = session.post(
        f"{REEF_API}/jenkins/start_jenkins_job",
        json={"jobName": job_name},
    )
    if not r.ok:
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    return {"ok": True}
```

- [ ] **Step 4: Commit**

```bash
git add scripts/pantheon-cli
git commit -m "refactor: replace write operation XHR with direct requests calls"
```

---

## Task 7: Migrate all Reef commands to `get_reef_session()`

**Files:**
- Modify: `scripts/pantheon-cli`

Replace the `open_pantheon()` + `try/finally` pattern in each command with a simple `get_reef_session()` call. Update all function calls that now take `session` instead of `page`.

- [ ] **Step 1: Migrate `cmd_list`**

Find `def cmd_list(args):` and replace the entire function:

```python
def cmd_list(args):
    """List titles for a product/version."""
    session = get_reef_session(args)

    titles = get_titles(session, args.product, args.version)
    titles = filter_titles(titles, args.title)
    print(f"{'Name':<70} {'Env':<8} {'State':<10} {'Branch':<30} {'Content Dir'}")
    print("-" * 160)

    for t in titles:
        name = t['name']
        for env_name in ['preview', 'stage']:
            job = t.get('jobs', {}).get(env_name, {})
            state = job.get('state', 'N/A') or 'N/A'
            branch = job.get('gitBranch', 'N/A') or 'N/A'
            if env_name == args.env or args.env == 'preview':
                config = get_build_config(session, t['uuid'], env_name)
                content_dir = config.get('contentDirectory', 'N/A')
            else:
                content_dir = ''
            print(f"{name:<70} {env_name:<8} {state:<10} {branch:<30} {content_dir}")
```

- [ ] **Step 2: Migrate `cmd_update`**

Find `def cmd_update(args):` and replace the entire function:

```python
def cmd_update(args):
    """Update build configuration for titles."""
    if not args.branch and not args.directory and not args.enable:
        print("ERROR: Specify at least --branch, --directory, or --enable.")
        sys.exit(1)

    session = get_reef_session(args)

    titles = get_titles(session, args.product, args.version)
    titles = filter_titles(titles, args.title)
    print(f"Found {len(titles)} matching titles\n")

    if not titles:
        print("No titles match the filter.")
        return

    updates = []
    for t in titles:
        config = get_build_config(session, t['uuid'], args.env)
        job = t.get('jobs', {}).get(args.env, {})
        job_name = job.get('jobName', '')
        state = job.get('state', '')

        current_branch = config.get('branch', '')
        current_dir = config.get('contentDirectory', '')
        content_type = config.get('contentType', 'book')

        new_branch = args.branch or current_branch
        new_dir = args.directory or current_dir

        needs_config = (new_branch != current_branch or new_dir != current_dir)
        needs_enable = (args.enable and state == 'DISABLED')

        if needs_config or needs_enable:
            updates.append({
                'name': t['name'],
                'uuid': t['uuid'],
                'current_branch': current_branch,
                'current_dir': current_dir,
                'new_branch': new_branch,
                'new_dir': new_dir,
                'content_type': content_type,
                'job_name': job_name,
                'needs_config': needs_config,
                'needs_enable': needs_enable,
                'state': state,
            })

    if not updates:
        print("All titles are already up to date.")
        return

    print(f"{'=' * 60}")
    print(f"{'[DRY RUN] ' if not args.exec else ''}Updates for {len(updates)} titles:")
    print(f"{'=' * 60}")

    for t in updates:
        print(f"\n  {t['name']}")
        if t['needs_config']:
            if t['current_branch'] != t['new_branch']:
                print(f"    branch: {t['current_branch']} -> {t['new_branch']}")
            if t['current_dir'] != t['new_dir']:
                print(f"    dir:    {t['current_dir']} -> {t['new_dir']}")
        if t['needs_enable']:
            print(f"    enable: DISABLED -> ENABLED")

    if not args.exec:
        print(f"\nDry run. Use --exec to apply changes.")
        return

    success = 0
    fail = 0
    for i, t in enumerate(updates):
        print(f"\n[{i+1}/{len(updates)}] {t['name']}")

        try:
            if t['needs_config']:
                update_build_config(
                    session, t['uuid'], args.env,
                    t['new_branch'], t['new_dir'], t['content_type']
                )
                print("  Config updated")

            if t['needs_enable']:
                result = toggle_job(session, t['job_name'], True)
                if result.get('ok'):
                    print("  Enabled")
                else:
                    print(f"  Enable failed: {result.get('error')}")

            if args.rebuild and t['job_name']:
                result = start_build(session, t['job_name'])
                if result.get('ok'):
                    print("  Rebuild triggered")
                else:
                    print(f"  Rebuild failed: {result.get('error')}")

            success += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            fail += 1

        time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"Done. Success: {success}, Failed: {fail}")
```

- [ ] **Step 3: Migrate `cmd_rebuild`**

Find `def cmd_rebuild(args):` and replace the entire function:

```python
def cmd_rebuild(args):
    """Trigger rebuilds for titles."""
    session = get_reef_session(args)

    titles = get_titles(session, args.product, args.version)
    titles = filter_titles(titles, args.title)
    print(f"Found {len(titles)} matching titles\n")

    jobs = []
    for t in titles:
        job = t.get('jobs', {}).get(args.env, {})
        job_name = job.get('jobName', '')
        state = job.get('state', '')
        if not job_name:
            continue
        needs_enable = (args.enable and state == 'DISABLED')
        jobs.append({
            'name': t['name'],
            'job_name': job_name,
            'state': state,
            'needs_enable': needs_enable,
        })

    disabled = [j for j in jobs if j['needs_enable']]
    print(f"Jobs to rebuild: {len(jobs)}")
    if disabled:
        print(f"Jobs to enable:  {len(disabled)}")

    if not args.exec:
        print(f"\nDry run. Titles that would be rebuilt:")
        for j in jobs:
            enable_tag = " [ENABLE]" if j['needs_enable'] else ""
            print(f"  {j['name']} ({j['state']}){enable_tag}")
        print(f"\nUse --exec to apply.")
        return

    if disabled:
        print(f"\nEnabling {len(disabled)} disabled jobs...")
        for j in disabled:
            result = toggle_job(session, j['job_name'], True)
            status = "OK" if result.get('ok') else f"FAIL: {result.get('error')}"
            print(f"  {j['name']}: {status}")
            time.sleep(1)

    print(f"\nTriggering {len(jobs)} rebuilds...")
    success = 0
    fail = 0
    for j in jobs:
        result = start_build(session, j['job_name'])
        if result.get('ok'):
            print(f"  {j['name']}: triggered")
            success += 1
        else:
            print(f"  {j['name']}: FAIL: {result.get('error')}")
            fail += 1
        time.sleep(1)

    if args.wait and success > 0:
        print(f"\nWaiting for builds to complete (timeout: {args.timeout}s)...")
        deadline = time.time() + args.timeout
        pending = {j['name'] for j in jobs if j['job_name']}

        while pending and time.time() < deadline:
            time.sleep(10)
            fresh_titles = get_titles(session, args.product, args.version)
            for t in fresh_titles:
                if t['name'] in pending:
                    job = t.get('jobs', {}).get(args.env, {})
                    state = job.get('state', '')
                    if state in ('SUCCESS', 'FAILURE', 'DISABLED'):
                        status = "OK" if state == 'SUCCESS' else state
                        print(f"  {t['name']}: {status}")
                        pending.discard(t['name'])

            remaining = len(pending)
            if remaining > 0:
                elapsed = int(time.time() - (deadline - args.timeout))
                print(f"  ... {remaining} still building ({elapsed}s)")

        if pending:
            print(f"\nTIMEOUT: {len(pending)} builds did not complete:")
            for name in sorted(pending):
                print(f"  {name}")

    print(f"\nDone. Triggered: {success}, Failed: {fail}")
```

- [ ] **Step 4: Migrate `cmd_publish`**

Find `def cmd_publish(args):` and replace the entire function:

```python
def cmd_publish(args):
    """Enable and rebuild stage builds for a release."""
    args.env = 'stage'
    args.enable = True

    if not args.exec:
        print("Publish operates on STAGE environment.")
        print("This will enable all stage jobs and trigger rebuilds.\n")

    if args.rebuild_first:
        args.wait = getattr(args, 'wait', False)
        args.timeout = getattr(args, 'timeout', 300)
        cmd_rebuild(args)
    else:
        session = get_reef_session(args)
        titles = get_titles(session, args.product, args.version)
        titles = filter_titles(titles, args.title)

        disabled = []
        for t in titles:
            job = t.get('jobs', {}).get('stage', {})
            if job.get('state') == 'DISABLED':
                disabled.append(t['name'])

        print(f"Titles: {len(titles)}")
        print(f"Disabled stage jobs: {len(disabled)}")

        if not args.exec:
            if disabled:
                print(f"\nWould enable:")
                for name in disabled:
                    print(f"  {name}")
            print(f"\nUse --exec to enable. Add --rebuild-first to also trigger builds.")
            return

        if disabled:
            print(f"\nEnabling {len(disabled)} stage jobs...")
            for t in titles:
                job = t.get('jobs', {}).get('stage', {})
                if job.get('state') == 'DISABLED':
                    job_name = job.get('jobName', '')
                    if job_name:
                        result = toggle_job(session, job_name, True)
                        status = "OK" if result.get('ok') else "FAIL"
                        print(f"  {t['name']}: {status}")
                        time.sleep(1)

        print("\nDone. Stage jobs enabled.")
        print("Use --rebuild-first to also trigger builds.")
```

- [ ] **Step 5: Run the tests to confirm nothing broke**

```bash
venv/bin/pytest tests/test_reef_auth.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/pantheon-cli
git commit -m "feat: migrate reef commands to cookie-based requests auth"
```

---

## Task 8: Remove `open_pantheon()` and `SESSION_DIR`

**Files:**
- Modify: `scripts/pantheon-cli`

`open_pantheon()` is no longer called by any command. `SESSION_DIR` is no longer used.

- [ ] **Step 1: Delete `open_pantheon()` from `scripts/pantheon-cli`**

Remove the entire function (from `def open_pantheon(args):` through its closing `return p, browser, page`).

- [ ] **Step 2: Remove `SESSION_DIR` constant**

Find and delete:
```python
SESSION_DIR = str(Path.home() / ".cache" / "pantheon-session")
```

- [ ] **Step 3: Verify no remaining references**

```bash
grep -n "open_pantheon\|SESSION_DIR" scripts/pantheon-cli
```

Expected: no output.

- [ ] **Step 4: Run the tests**

```bash
venv/bin/pytest tests/test_reef_auth.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Smoke test the list command (requires VPN + Kerberos + Chrome session)**

```bash
pantheon-cli list --version 1.9
```

Expected: authenticates (Playwright headless if no cache), then lists titles. First run will do Playwright login; subsequent runs will use `~/.cache/pantheon-reef-cookies.json`.

- [ ] **Step 6: Commit**

```bash
git add scripts/pantheon-cli
git commit -m "refactor: remove open_pantheon() and SESSION_DIR"
```

---

## Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the Architecture section in `CLAUDE.md`**

Find the "Two authentication layers" section and replace it:

```markdown
**Two authentication layers:**

- **Reef API commands** (`list`, `update`, `rebuild`, `publish`): Authenticate using Playwright Firefox headless with Kerberos SPNEGO (same as splash commands). Cookies are extracted and cached to `~/.cache/pantheon-reef-cookies.json` (8-hour TTL). All Reef API calls are then made via `requests` using those cookies — no XHR or Angular service calls.

- **Splash commands** (`splash-export`, `splash-configure`): Same Playwright auth flow, cookies cached to `~/.cache/pantheon-splash-cookies.json`. DSPM API calls via `requests`.

Both auth layers use the headless→headed fallback pattern and the `--fresh` flag to force re-authentication.
```

Also update the `Session persistence` line in Key Behavior:

```markdown
- **Session persistence**: `~/.cache/pantheon-reef-cookies.json` (Reef) and `~/.cache/pantheon-splash-cookies.json` (splash). Use `--fresh` to clear and re-authenticate.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to reflect cookie-based reef auth"
```
