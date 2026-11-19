#!/usr/bin/env python3
"""Bump the skill's version in SKILL.md and add an entry to CHANGELOG.md.

Usage:
  bump_version.py patch|minor|major "What changed" ["Another change" ...]
  bump_version.py --show
"""

import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
CHANGELOG = ROOT / "CHANGELOG.md"
VERSION_LINE = re.compile(r"^(\s+version:\s*)(\d+)\.(\d+)\.(\d+)\s*$", re.M)
UPDATED_LINE = re.compile(r"^(\s+updated:\s*).*$", re.M)


def current(text):
    match = VERSION_LINE.search(text)
    if not match:
        sys.exit("No `version:` under `metadata:` in SKILL.md's frontmatter.")
    return tuple(int(n) for n in match.groups()[1:])


def main(argv):
    text = SKILL.read_text()
    if argv == ["--show"]:
        print(".".join(map(str, current(text))))
        return 0
    if len(argv) < 2 or argv[0] not in ("patch", "minor", "major"):
        sys.exit(__doc__.strip())
    major, minor, patch = current(text)
    if argv[0] == "major":
        major, minor, patch = major + 1, 0, 0
    elif argv[0] == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    version = f"{major}.{minor}.{patch}"
    today = datetime.date.today().isoformat()

    text = VERSION_LINE.sub(lambda m: m.group(1) + version, text, count=1)
    text = UPDATED_LINE.sub(lambda m: m.group(1) + today, text, count=1)
    SKILL.write_text(text)

    entry = f"## {version} ({today})\n\n" + "".join(f"- {note}\n" for note in argv[1:]) + "\n"
    log = CHANGELOG.read_text()
    first = log.find("\n## ")
    log = log[: first + 1] + entry + log[first + 1 :] if first >= 0 else log.rstrip() + "\n\n" + entry
    CHANGELOG.write_text(log)
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
