#!/usr/bin/env python3
"""
BRAIN Operator Lookup Script

Fetches operator definitions from the WorldQuant BRAIN API.

Requires authentication (BRAIN session token). The token can be obtained
by logging into platform.worldquantbrain.com and extracting from browser
cookies/localStorage.

Usage:
    python3 lookup_operator.py <operator-name>
    python3 lookup_operator.py --list
    python3 lookup_operator.py --search <keyword>
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


API_BASE = "https://api.worldquantbrain.com"
TOKEN_ENV_VAR = "BRAIN_AUTH_TOKEN"


def get_token():
    """Get auth token from environment variable."""
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        print(f"Error: Set {TOKEN_ENV_VAR} environment variable with your BRAIN auth token.",
              file=sys.stderr)
        print("Tip: Login to platform.worldquantbrain.com, open DevTools -> Application ->",
              file=sys.stderr)
        print("     Local Storage, find the auth key, and export it:", file=sys.stderr)
        print(f"     export {TOKEN_ENV_VAR}='your_token_here'", file=sys.stderr)
        sys.exit(1)
    return token


def api_request(path):
    """Make authenticated request to BRAIN API."""
    token = get_token()
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def list_operators():
    """List all available operators."""
    data = api_request("/operators")
    if isinstance(data, list):
        for op in data:
            print(f"  {op.get('name', '?')}: {op.get('description', '')[:100]}")
    else:
        print(json.dumps(data, indent=2))


def search_operators(keyword):
    """Search operators by keyword."""
    data = api_request(f"/operators?search={keyword}")
    if isinstance(data, list):
        for op in data:
            print(f"  {op.get('name', '?')}: {op.get('description', '')[:100]}")
    else:
        print(json.dumps(data, indent=2))


def get_operator(name):
    """Get definition of a specific operator."""
    data = api_request(f"/operators/{name}")
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Look up BRAIN operator definitions")
    parser.add_argument("name", nargs="?", help="Operator name to look up")
    parser.add_argument("--list", action="store_true", help="List all operators")
    parser.add_argument("--search", metavar="KEYWORD", help="Search operators by keyword")

    args = parser.parse_args()

    if args.list:
        list_operators()
    elif args.search:
        search_operators(args.search)
    elif args.name:
        get_operator(args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
