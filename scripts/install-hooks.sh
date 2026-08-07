#!/bin/sh
# Install the repository's git hooks.
#
# .git/hooks is not tracked, so a fresh clone has no hooks until this runs.
# Uses core.hooksPath rather than copying files into .git/hooks, so the hooks
# stay versioned and a later `git pull` picks up changes to them automatically
# — a copied hook silently goes stale, which is the failure mode that matters
# for a guard.
#
# Run:  make hooks     (or: sh scripts/install-hooks.sh)

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

echo "hooks installed: core.hooksPath -> .githooks"
echo
echo "active hooks:"
for h in .githooks/*; do
    [ -f "$h" ] && echo "  $(basename "$h")"
done
echo
echo "Bypass one commit with: git commit --no-verify"
echo "Uninstall with:         git config --unset core.hooksPath"
