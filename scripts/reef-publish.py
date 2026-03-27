#!/usr/bin/env python3
"""
Reef/Pantheon title publisher.

Automates SAML login via headless browser to obtain a session cookie,
then uses the Reef API to list and publish titles.

Usage:
    reef-publish.py login                          # Login and cache session
    reef-publish.py list <product>                 # List titles for a product
    reef-publish.py publish <product> [--version V] [--title T] [--env ENV]
    reef-publish.py products                       # List all products

Examples:
    reef-publish.py login
    reef-publish.py list red_hat_enterprise_linux_ai
    reef-publish.py publish red_hat_enterprise_linux_ai --version 1.4 --title getting_started --env stage
    reef-publish.py publish red_hat_enterprise_linux_ai --version 1.4  # publish all titles for version
"""

import argparse
import json
import sys
import time
from pathlib import Path

import browser_cookie3
import requests

REEF_URL = "https://reef.corp.redhat.com"
PANTHEON_URL = "https://pantheon.cee.redhat.com"
COOKIE_FILE = Path.home() / ".reef-session"
AUTH_COOKIE_NAMES = ("pantheon-auth", "pantheon-session", "reef-session", "rh_sso_session")


def get_cached_cookies():
    """Read cached cookies if they exist and are recent enough."""
    if not COOKIE_FILE.exists():
        return None
    age = time.time() - COOKIE_FILE.stat().st_mtime
    if age > 8 * 3600:
        print("Cached session expired, re-login required.", file=sys.stderr)
        return None
    return json.loads(COOKIE_FILE.read_text())


def save_cookies(cookies_dict):
    """Cache the session cookies to disk."""
    COOKIE_FILE.write_text(json.dumps(cookies_dict))
    COOKIE_FILE.chmod(0o600)
    print(f"Session saved to {COOKIE_FILE}")


def login():
    """Extract auth cookies from Chrome's cookie database."""
    print("Reading auth cookies from Chrome...")

    cj = browser_cookie3.chrome(domain_name=".redhat.com")
    cookies = {}
    for c in cj:
        if c.name in AUTH_COOKIE_NAMES:
            cookies[c.name] = c.value

    if "pantheon-auth" not in cookies:
        print("No 'pantheon-auth' cookie found in Chrome.", file=sys.stderr)
        print("Make sure you are logged into Pantheon in Chrome.", file=sys.stderr)
        sys.exit(1)

    save_cookies(cookies)
    print(f"Login successful! ({len(cookies)} cookies captured)")
    return cookies


def get_session():
    """Get a requests.Session with the reef auth cookies."""
    cookies = get_cached_cookies()
    if not cookies:
        print("No valid session found. Run: reef-publish.py login", file=sys.stderr)
        sys.exit(1)
    s = requests.Session()
    for name, value in cookies.items():
        s.cookies.set(name, value, domain=".redhat.com")
    s.verify = False
    return s


def api_get(path, params=None):
    """Make authenticated GET request to Reef API."""
    s = get_session()
    r = s.get(f"{REEF_URL}/api/{path}", params=params)
    r.raise_for_status()
    return r.json()


def api_post(path, data=None):
    """Make authenticated POST request to Reef API."""
    s = get_session()
    r = s.post(f"{REEF_URL}/api/{path}", json=data)
    r.raise_for_status()
    return r.json()


def cmd_login(_args):
    login()


def cmd_products(_args):
    data = api_get("lightblue/get_products")
    products = data.get("data", [])
    print(f"{'Product':<60} {'URL Fragment'}")
    print("-" * 90)
    for p in sorted(products, key=lambda x: x["name"]):
        print(f"{p['displayName']:<60} {p['urlFragment']}")


def cmd_list(args):
    data = api_get("lightblue/get_titles", params={
        "lang": "en-US",
        "product": args.product,
    })
    products = data.get("data", {}).get("products", [])
    if not products:
        print(f"No titles found for product: {args.product}")
        return

    for prod in products:
        print(f"\n{prod['name']}")
        print("=" * len(prod["name"]))
        for ver in sorted(prod["versions"], key=lambda v: v["name"], reverse=True):
            print(f"\n  Version {ver['name']}:")
            for title in ver["titles"]:
                envs = title.get("environments", {})
                env_status = []
                for env_name in ["preview", "stage", "prod"]:
                    env = envs.get(env_name, {})
                    locales = env.get("locales", [])
                    status = locales[-1]["status"] if locales else "n/a"
                    env_status.append(f"{env_name}={status}")
                print(f"    {title['urlFragment']:<50} [{', '.join(env_status)}]")
                print(f"      uuid: {title['uuid']}")


def cmd_publish(args):
    data = api_get("lightblue/get_titles", params={
        "lang": "en-US",
        "product": args.product,
    })
    products = data.get("data", {}).get("products", [])
    if not products:
        print(f"No titles found for product: {args.product}")
        return

    targets = []
    for prod in products:
        for ver in prod["versions"]:
            if args.version and ver["name"] != args.version:
                continue
            for title in ver["titles"]:
                if args.title and title["urlFragment"] != args.title:
                    continue
                targets.append({
                    "version": ver["name"],
                    "name": title["name"],
                    "urlFragment": title["urlFragment"],
                    "uuid": title["uuid"],
                })

    if not targets:
        print("No matching titles found.")
        print("Use 'list' command to see available titles.")
        return

    env = args.env or "stage"
    print(f"\nWill publish {len(targets)} title(s) to {env}:\n")
    for t in targets:
        print(f"  [{t['version']}] {t['name']} ({t['urlFragment']})")

    print()
    confirm = input("Proceed? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    for t in targets:
        print(f"Publishing {t['name']} ({t['version']})...", end=" ", flush=True)
        try:
            result = api_post("lightblue/publish_title", data={
                "uuid": t["uuid"],
                "environment": env,
            })
            print("OK")
            if "message" in result:
                print(f"  -> {result['message']}")
        except requests.exceptions.HTTPError as e:
            print(f"FAILED: {e}")
            try:
                print(f"  -> {e.response.json().get('message', '')}")
            except Exception:
                pass


def main():
    # Suppress SSL warnings for internal certs
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    parser = argparse.ArgumentParser(
        description="Reef/Pantheon title publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="Grab session cookie from Chrome")
    sub.add_parser("products", help="List all products")

    p_list = sub.add_parser("list", help="List titles for a product")
    p_list.add_argument("product", help="Product URL fragment (e.g. red_hat_enterprise_linux_ai)")

    p_pub = sub.add_parser("publish", help="Publish titles")
    p_pub.add_argument("product", help="Product URL fragment")
    p_pub.add_argument("--version", "-v", help="Version to publish (e.g. 1.4)")
    p_pub.add_argument("--title", "-t", help="Specific title URL fragment to publish")
    p_pub.add_argument("--env", "-e", default="stage", choices=["preview", "stage", "prod"],
                        help="Target environment (default: stage)")

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "products": cmd_products,
        "list": cmd_list,
        "publish": cmd_publish,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
