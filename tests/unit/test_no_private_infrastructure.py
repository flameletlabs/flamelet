"""CI guard: no private infrastructure in tracked files.

The detection itself lives in core/privacy_scan.py so that the pre-commit hook
enforces exactly the same rules — see that module for why the two must share
code rather than each holding a copy.

What lives HERE is what keeps the detector honest: every check is fired at a
planted positive, and the file walk is asserted non-empty. A check that cannot
fail is not a check.
"""

import subprocess
from pathlib import Path

import pytest

from core.privacy_scan import CHECKS, NEVER_TRACKED, REPO_ROOT, tracked_text_files


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


@pytest.mark.parametrize("rel", NEVER_TRACKED)
def test_privacy_working_file_is_not_tracked(rel):
    """The guard's own token files must not be in the repository at all."""
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode != 0, (
        f"{rel} is TRACKED. It holds the private tokens this guard exists to "
        "keep out of a public repository, and no content check can catch it — "
        "remove it from the index and from history."
    )


@pytest.mark.parametrize("rel", NEVER_TRACKED)
def test_privacy_working_file_is_gitignored(rel):
    """...and .gitignore must keep them from being added by accident.

    Not tracked today is not the same as safe: `git add -A` stages anything
    untracked-and-unignored. On 2026-08-16 .privacy-local was exactly that —
    untracked, NOT ignored, staged by `git add -A --dry-run`, and passed by
    both the hook and CI, because the content checks match hostname shape
    (label.tld) and it holds bare TLDs. Its own header claimed .gitignore
    covered it while `git check-ignore` returned 1.
    """
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0, (
        f"{rel} is NOT gitignored, so `git add -A` would stage it and neither "
        "the pre-commit hook nor the content checks would object. Add it to "
        ".gitignore beside the other privacy working files."
    )


def test_content_checks_cannot_see_a_bare_tld_list():
    """The reason the two tests above must exist, asserted rather than trusted.

    If a content check ever DOES fire on a bare-TLD list, this fails loudly and
    the path-based bar can be reconsidered. Until then it is the only defence,
    and a comment claiming so would rot silently.

    ⚠️ The sample uses FICTIONAL labels on purpose. The first version of this
    test wrote three of the estate's real private TLDs in — which published the
    naming scheme into this public repository, i.e. exactly what NEVER_TRACKED
    exists to prevent, and the guard could not object because a bare TLD is the
    blind spot this test is about. What is being asserted is a SHAPE (a leading
    dot with no label in front), so any label works and a real one buys nothing.
    """
    bare = "\n".join(sorted({".example", ".invalid", ".nonesuch"})) + "\n"
    firing = [name for name, (finder, _) in CHECKS.items() if finder(bare, False)]
    assert not firing, (
        f"checks {firing} now fire on a bare-TLD list. The premise of "
        "NEVER_TRACKED has changed — re-read whether path-barring is still "
        "the right mechanism."
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
