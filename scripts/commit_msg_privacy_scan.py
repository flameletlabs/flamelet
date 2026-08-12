#!/usr/bin/env python3
"""commit-msg hook: refuse a commit whose MESSAGE carries private infrastructure.

WHY A THIRD HOOK
----------------
CLAUDE.md has always said the rule covers commit messages -- "not in code, not
in tests, not in docs, not in comments, and not in commit messages" -- but the
two existing layers both scan FILE CONTENT. The message was the one surface that
stated the rule without checking it, and a rule stated but not checked is the one
that gets broken.

Install:

    ln -sf ../../scripts/commit_msg_privacy_scan.py .git/hooks/commit-msg

⚠️ This cannot retroactively clean a message that already landed, for the same
reason the pre-commit hook cannot clean a file: rewriting published history is a
separate and disruptive act. It stops the NEXT one.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.privacy_scan import commit_message_violations  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("usage: commit_msg_privacy_scan.py <path-to-message-file>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        message = path.read_text()
    except OSError as exc:
        print(f"cannot read commit message: {exc}", file=sys.stderr)
        return 2

    # Comment lines are stripped by git before the message is stored, so they
    # cannot leak. Scanning them would flag the diff git helpfully includes.
    body = "\n".join(ln for ln in message.splitlines() if not ln.startswith("#"))

    violations = commit_message_violations(body)
    if not violations:
        return 0

    print("COMMIT BLOCKED - private infrastructure in the commit MESSAGE.\n", file=sys.stderr)
    for check, match in violations:
        print(f"  [{check}] {match}", file=sys.stderr)
    print(
        "\nflamelet is a public repository - see the MANDATORY section at the top\n"
        "of CLAUDE.md. The rule covers commit messages, not just files.\n"
        "\n"
        "Use example.com hostnames and 192.0.2.0/24 style addresses, or describe\n"
        "the change without the identifier.\n"
        "\n"
        "To bypass deliberately: git commit --no-verify\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
