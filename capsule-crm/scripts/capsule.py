#!/usr/bin/env python3
"""Small, dependency-free client for the Capsule CRM REST API v2.

Usage:
  capsule.py get PATH [-p key=value ...] [--all] [--max-pages N]
  capsule.py post|put PATH --data JSON|@file.json --confirm [-p key=value ...]
  capsule.py delete PATH --confirm
  capsule.py upload FILE --confirm [--type MIME]
  capsule.py whoami

PATH is relative to https://api.capsulecrm.com/api/v2 ("parties", "/kases/12"),
or a full https://api.capsulecrm.com URL (such as a Link header target).

The token comes from, in order: $CAPSULE_API_TOKEN, the file named by
$CAPSULE_TOKEN_FILE, a .capsule-token file in this directory or any parent, or
~/.config/capsule/token. It is never printed.

Output is JSON on stdout. Errors go to stderr with Capsule's message, and the
exit code is 1 (HTTP error), 2 (usage or setup) or 3 (rate limited).
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOST = "https://api.capsulecrm.com"
BASE = HOST + "/api/v2"

def skill_version():
    try:
        text = (Path(__file__).resolve().parent.parent / "SKILL.md").read_text()
        return re.search(r"^\s+version:\s*(\S+)", text, re.M).group(1)
    except (OSError, AttributeError):
        return "unknown"


USER_AGENT = f"capsule-crm-skill/{skill_version()}"
MAX_RATE_RETRIES = 3
MAX_WAIT_SECONDS = 60


class CapsuleError(Exception):
    def __init__(self, message, status=None, exit_code=1):
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code


# MARK: Token

def find_token():
    token = os.environ.get("CAPSULE_API_TOKEN", "").strip()
    if token:
        return token
    candidates = []
    if os.environ.get("CAPSULE_TOKEN_FILE"):
        candidates.append(Path(os.environ["CAPSULE_TOKEN_FILE"]).expanduser())
    here = Path.cwd()
    candidates += [d / ".capsule-token" for d in [here, *here.parents]]
    candidates.append(Path.home() / ".config" / "capsule" / "token")
    for path in candidates:
        if path.is_file():
            token = path.read_text().strip()
            if token:
                return token
    raise CapsuleError(
        "No Capsule token. Set CAPSULE_API_TOKEN, or put a personal access token "
        "(Capsule: My Preferences > API Authentication Tokens) in .capsule-token "
        "or ~/.config/capsule/token.",
        exit_code=2,
    )


# MARK: URLs and paging

def build_url(path, params=None):
    if path.startswith("https://"):
        if not path.startswith(HOST + "/"):
            raise CapsuleError(f"Refusing to send the token to {path}", exit_code=2)
        url = path
    else:
        url = BASE + "/" + path.lstrip("/")
    if params:
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        keys = {k for k, _ in params}
        query = [(k, v) for k, v in query if k not in keys] + list(params)
        # Keep commas readable: embed=tags,fields
        url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query, safe=",:")))
    return url


def next_link(header):
    """The rel="next" target of a Link header.

    URLs can contain commas (embed=tags,fields), so targets are read between < and >,
    never by splitting the header on commas. rel may be quoted, unquoted or hold several
    values, and a relative target resolves against the API host.
    """
    if not header:
        return None
    for match in re.finditer(r"<([^>]*)>([^<]*)", header):
        target, params = match.group(1), match.group(2)
        rel = re.search(r'rel\s*=\s*(?:"([^"]*)"|([^;,\s]+))', params)
        if rel and "next" in (rel.group(1) or rel.group(2) or "").split():
            return urllib.parse.urljoin(HOST + "/", target)
    return None


def following_page(url):
    """The same URL with page set to one more than its current value (1 when absent)."""
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    current = next((int(v) for k, v in query if k == "page" and v.isdigit()), 1)
    query = [(k, v) for k, v in query if k != "page"] + [("page", str(current + 1))]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query, safe=",:")))


# MARK: Requests

def error_message(status, body):
    """Capsule's `message` then each `errors[].message`, skipping blanks."""
    parts = []
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            parts.append(data.get("message") or data.get("error_description") or data.get("error"))
            for err in data.get("errors") or []:
                if isinstance(err, dict):
                    parts.append(err.get("message"))
    except (ValueError, TypeError):
        pass
    text = " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
    return f"HTTP {status}: {text}" if text else f"HTTP {status}"


def rate_limit_wait(headers):
    retry_after = headers.get("Retry-After")
    if retry_after and retry_after.strip().isdigit():
        wait = int(retry_after)
    elif (headers.get("X-RateLimit-Reset") or "").strip().isdigit():
        wait = int(headers["X-RateLimit-Reset"]) - int(time.time())
    else:
        wait = 5
    return max(1, wait)


def request(method, url, token, body=None, content_type=None, extra_headers=None):
    """Send one request. Returns (status, headers, raw body bytes)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if body is not None:
        headers["Content-Type"] = content_type or "application/json"
    headers.update(extra_headers or {})
    for attempt in range(MAX_RATE_RETRIES + 1):
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code == 429:
                wait = rate_limit_wait(e.headers)
                if attempt < MAX_RATE_RETRIES and wait <= MAX_WAIT_SECONDS:
                    print(f"Rate limited; waiting {wait}s", file=sys.stderr)
                    time.sleep(wait)
                    continue
                raise CapsuleError(
                    f"Rate limited by Capsule (4,000 requests/hour per user); try again in {wait}s.",
                    status=429, exit_code=3,
                )
            message = error_message(e.code, raw)
            if e.code == 500 and method in ("POST", "PUT"):
                message = (f"HTTP 500: Capsule couldn't save the change. It may hold characters "
                           f"Capsule can't store (above U+FFFF, such as emoji).")
            raise CapsuleError(message, status=e.code)
        except urllib.error.URLError as e:
            raise CapsuleError(f"Network error: {e.reason}")
    raise AssertionError("unreachable")


def decode(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw.decode("utf-8", "replace")}


def get_all(url, token, max_pages):
    """Follow pages and merge the list under the response's single list key."""
    merged, key, pages = None, None, 0
    while url and pages < max_pages:
        _, headers, raw = request("GET", url, token)
        data = decode(raw) or {}
        pages += 1
        lists = [k for k, v in data.items() if isinstance(v, list)]
        if merged is None:
            merged = data
            key = lists[0] if len(lists) == 1 else None
            if key is None:
                return merged  # not a list response
        else:
            merged[key].extend(data.get(key) or [])
        items = data.get(key) or []
        nxt = next_link(headers.get("Link"))
        per_page = int(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get("perPage", 50))
        # A full page with no next link: ask for the following page anyway.
        if not nxt and items and len(items) >= per_page:
            nxt = following_page(url)
        url = nxt
    if url:
        print(f"Stopped after {max_pages} pages; more remain (raise --max-pages).", file=sys.stderr)
    return merged


# MARK: Commands

def parse_params(pairs):
    params = []
    for pair in pairs or []:
        if "=" not in pair:
            raise CapsuleError(f"Bad parameter {pair!r}; use key=value", exit_code=2)
        k, v = pair.split("=", 1)
        params.append((k, v))
    return params


def unstorable(value):
    """Characters above U+FFFF anywhere in a decoded JSON value, in order, once each.

    Capsule can't store them: most fields save "��" instead, and some fail with a 500.
    """
    found = []
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            found += [ch for ch in item if ord(ch) > 0xFFFF and ch not in found]
        elif isinstance(item, dict):
            stack += reversed(list(item.values()))
        elif isinstance(item, list):
            stack += reversed(item)
    return found


def load_data(data, check_text=True):
    if data is None:
        raise CapsuleError("This command needs --data", exit_code=2)
    text = Path(data[1:]).read_text() if data.startswith("@") else data
    try:
        value = json.loads(text)
    except ValueError as e:
        raise CapsuleError(f"--data is not valid JSON: {e}", exit_code=2)
    bad = unstorable(value) if check_text else []
    if bad:
        raise CapsuleError(
            "Capsule can't store these characters (above U+FFFF, such as most emoji): "
            + " ".join(bad) + ". Ask the user to remove or replace them.",
            exit_code=2,
        )
    return text.encode("utf-8")


def require_confirm(args):
    if not args.confirm:
        raise CapsuleError(
            f"{args.command.upper()} changes the live Capsule account. "
            "Re-run with --confirm once the user has approved this change.",
            exit_code=2,
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Capsule CRM API v2 client")
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("get", help="GET a resource")
    g.add_argument("path")
    g.add_argument("-p", "--param", action="append", help="query parameter key=value")
    g.add_argument("--all", action="store_true", help="follow every page and merge")
    g.add_argument("--max-pages", type=int, default=50)

    for name in ("post", "put"):
        w = sub.add_parser(name, help=f"{name.upper()} JSON")
        w.add_argument("path")
        w.add_argument("--data", help="JSON body, or @file.json")
        w.add_argument("-p", "--param", action="append")
        w.add_argument("--confirm", action="store_true")
        w.add_argument("--all", action="store_true",
                       help="(post only) follow pages of a filters/results query")
        w.add_argument("--max-pages", type=int, default=50)

    d = sub.add_parser("delete", help="DELETE a resource")
    d.add_argument("path")
    d.add_argument("--confirm", action="store_true")

    u = sub.add_parser("upload", help="upload a file for a note; prints its token")
    u.add_argument("file")
    u.add_argument("--type", help="MIME type (guessed from the name if left out)")
    u.add_argument("--confirm", action="store_true")

    sub.add_parser("whoami", help="the account and user the token belongs to")

    args = parser.parse_args(argv)
    try:
        token = find_token()
        if args.command == "whoami":
            site = decode(request("GET", build_url("site"), token)[2]) or {}
            user = decode(request("GET", build_url("users/current"), token)[2]) or {}
            out = {"site": site.get("site"), "user": user.get("user")}
        elif args.command == "get":
            params = parse_params(args.param)
            if args.all and not any(k == "perPage" for k, _ in params):
                params.append(("perPage", "100"))
            url = build_url(args.path, params)
            out = get_all(url, token, args.max_pages) if args.all else decode(request("GET", url, token)[2])
        elif args.command in ("post", "put"):
            is_query = args.command == "post" and args.path.rstrip("/").endswith("filters/results")
            if not is_query:
                require_confirm(args)
            body = load_data(args.data, check_text=not is_query)
            params = parse_params(args.param)
            if is_query and args.all:
                params = [p for p in params if p[0] != "page"]
                if not any(k == "perPage" for k, _ in params):
                    params.append(("perPage", "100"))
                out, page = None, 1
                while page <= args.max_pages:
                    url = build_url(args.path, params + [("page", str(page))])
                    _, headers, raw = request("POST", url, token, body)
                    data = decode(raw) or {}
                    key = next((k for k, v in data.items() if isinstance(v, list)), None)
                    if out is None:
                        out = data
                    elif key:
                        out[key].extend(data[key])
                    per_page = int(dict(params).get("perPage", 100))
                    if not key or (not next_link(headers.get("Link")) and len(data[key]) < per_page):
                        break
                    page += 1
            else:
                status, headers, raw = request(args.command.upper(), build_url(args.path, params), token, body)
                out = decode(raw)
                if status == 202:
                    out = {"status": 202, "job": headers.get("Location"), "body": out}
        elif args.command == "delete":
            require_confirm(args)
            status, headers, raw = request("DELETE", build_url(args.path), token)
            out = {"status": status, "job": headers.get("Location")} if status == 202 else {"status": status}
        elif args.command == "upload":
            require_confirm(args)
            path = Path(args.file)
            mime = args.type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            _, _, raw = request(
                "POST", build_url("attachments/upload"), token, path.read_bytes(), mime,
                {"X-Attachment-Filename": urllib.parse.quote(path.name, safe="")},
            )
            out = decode(raw)
    except CapsuleError as e:
        print(str(e), file=sys.stderr)
        return e.exit_code
    if out is not None:
        json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
