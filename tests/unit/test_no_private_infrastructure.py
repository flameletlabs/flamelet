"""CI guard: no private infrastructure in tracked files.

The detection itself lives in core/privacy_scan.py so that the pre-commit hook
enforces exactly the same rules — see that module for why the two must share
code rather than each holding a copy.

What lives HERE is what keeps the detector honest: every check is fired at a
planted positive, and the file walk is asserted non-empty. A check that cannot
fail is not a check.
"""

from pathlib import Path

import pytest

from core.privacy_scan import CHECKS, REPO_ROOT, tracked_text_files


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_probe_fires_on_planted_violation(name):
    """Each probe must detect a known positive.

    Guards against the failure mode that made this file necessary: a probe
    that returns zero because it is broken, not because the repo is clean.
    """
    finder, planted = CHECKS[name]
    assert finder(planted, True), (
        f"probe {name!r} did NOT fire on its planted positive {planted!r}. "
        "Every clean result it reports is therefore meaningless."
    )


def test_guard_scans_itself():
    """This file must be inside its own scan.

    ``git ls-files`` lists only TRACKED files. While this module was still
    untracked it was silently excluded, so the explanatory comments in it —
    which quoted the very hostnames it forbids — passed locally and only failed
    once CI ran against the committed tree. An exemption here would recreate
    that blind spot permanently.
    """
    scanned = {rel for rel, _ in tracked_text_files()}
    me = str(Path(__file__).resolve().relative_to(REPO_ROOT))
    assert me in scanned, (
        f"{me} is not in its own scan (untracked?). Its contents would go "
        "unchecked, which is how the first version of this file shipped "
        "literal hostnames in its comments."
    )


def test_repo_has_scannable_files():
    """If the file walk silently yields nothing, every check passes vacuously."""
    files = list(tracked_text_files())
    assert len(files) > 50, f"only {len(files)} scannable files found; walk is broken"


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_no_private_infrastructure(name):
    finder, _ = CHECKS[name]
    hits = []
    for rel, text in tracked_text_files():
        for bad in finder(text, rel.endswith(".md")):
            hits.append(f"{rel}: {bad}")
    assert not hits, (
        f"{name}: private infrastructure found in tracked files.\n  "
        + "\n  ".join(sorted(set(hits))[:25])
        + "\n\nSee the MANDATORY section at the top of CLAUDE.md. If a hit is a "
        "genuine false positive, add it to the allowlist in this file WITH the "
        "reason — do not widen a pattern until it stops complaining."
    )
