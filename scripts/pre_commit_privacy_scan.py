#!/usr/bin/env python3
"""Block a commit that would put private infrastructure into history.

flamelet is a public repository. The CI guard
(tests/unit/test_no_private_infrastructure.py) catches leaks too — but only
AFTER the commit object exists, at which point sanitizing the tip no longer
removes the hostname from the commit that introduced it. That is why leaks kept
reappearing in history even with CI green. This runs first.

Both layers share their detection code (core/privacy_scan.py); neither keeps a
second copy of the patterns.

Scans the STAGED blob of each added/copied/modified file, not the working tree
— staged content is what the commit will actually contain, and the two can
differ when a file is edited after `git add`.

Install with `make hooks`. Bypass a single commit with `git commit --no-verify`
if you are certain; CI will still object.
"""

import subprocess
import sys
from pathlib import Path

# Only used to import the shared detector. Git commands deliberately run in
# the INHERITED cwd — git invokes hooks from the root of the repository being
# committed to, which is not necessarily where this script lives.
MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))

from core.privacy_scan import CHECKS, EXEMPT_PREFIXES, NEVER_TRACKED  # noqa: E402


def staged_files():
    """Paths staged for commit, excluding deletions and exempt trees."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p and not p.startswith(EXEMPT_PREFIXES)]


def staged_text(path):
    """The staged blob, or None if it is binary or unreadable as text."""
    blob = subprocess.run(["git", "show", f":{path}"], capture_output=True, check=False)
    if blob.returncode != 0:
        return None
    try:
        return blob.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None  # binary; nothing text-scannable


def main():
    staged = staged_files()

    # Path check first: these files are barred by NAME, because their content is
    # private tokens by design and every content check reads them as clean.
    barred = [p for p in staged if p in NEVER_TRACKED]
    if barred:
        print("\nCOMMIT BLOCKED - a privacy working file is staged.\n", file=sys.stderr)
        for path in barred:
            print(f"  {path}: must never be tracked in this public repository", file=sys.stderr)
        print(
            "\nThese hold the private tokens the guard exists to keep out, so the\n"
            "content scan below cannot judge them — they are barred by path.\n"
            "Unstage with:  git restore --staged <path>\n"
            "If one reached the index, .gitignore was edited or `git add -f` was\n"
            "used; fix that rather than bypassing this.\n",
            file=sys.stderr,
        )
        return 1

    findings = []
    for path in staged:
        text = staged_text(path)
        if text is None:
            continue
        is_md = path.endswith(".md")
        for name, (finder, _planted) in sorted(CHECKS.items()):
            for hit in finder(text, is_md):
                findings.append((path, name, hit))

    if not findings:
        return 0

    print("\nCOMMIT BLOCKED - private infrastructure in staged content.\n", file=sys.stderr)
    for path, name, hit in findings[:25]:
        print(f"  {path}: [{name}] {hit}", file=sys.stderr)
    if len(findings) > 25:
        print(f"  ... and {len(findings) - 25} more", file=sys.stderr)
    print(
        "\nflamelet is a public repository - see the MANDATORY section at the top\n"
        "of CLAUDE.md. Use example.com hostnames and 10.0.0.0/24 style addresses.\n"
        "\n"
        "If a hit is a genuine false positive, add it to the allowlist in\n"
        "core/privacy_scan.py WITH the reason - do not widen a pattern until it\n"
        "stops complaining.\n"
        "\n"
        "To bypass deliberately: git commit --no-verify  (CI will still object)\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
