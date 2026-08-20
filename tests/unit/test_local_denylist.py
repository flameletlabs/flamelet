"""The operator's own denylist.

The heuristics have to GUESS at hostnames, because CLAUDE.md forbids listing
private TLDs in this repository. That is why the private-TLD check is excluded
from commit-message scanning: over this repo's own history it produced ~30 false
positives. This closes that gap for an estate that opts in, without publishing
anything -- the list is untracked.
"""

from core.privacy_scan import (
    LOCAL_DENYLIST_FILE,
    load_local_denylist,
    local_denylist_violations,
)

# -- matching -------------------------------------------------------------


def test_tld_entry_matches_any_host_under_it():
    """One entry covers a whole site, rather than enumerating every host."""
    hits = local_denylist_violations("resolver on core" + ".demo-tld died", denylist=[".demo-tld"])
    assert hits == ["core" + ".demo-tld"]


def test_tld_entry_matches_several_hosts():
    text = "moved svc-a" + ".demo-tld and svc-b" + ".demo-tld"
    assert len(local_denylist_violations(text, denylist=[".demo-tld"])) == 2


def test_literal_entry_matches_exactly():
    assert local_denylist_violations("the box widget-01 rebooted", denylist=["widget-01"])


def test_matching_is_case_insensitive():
    assert local_denylist_violations("HOST-A" + ".DEMO-TLD", denylist=[".demo-tld"])


def test_unrelated_text_is_not_matched():
    """Exact matching means no false positives -- the whole point."""
    assert (
        local_denylist_violations("subprocess" + ".run and pytest" + ".ini", denylist=[".demo-tld"])
        == []
    )


# -- absence is normal, not an error --------------------------------------


def test_no_denylist_means_no_findings():
    """Most users have no such file; the guard must still work without one."""
    assert local_denylist_violations("anything", denylist=[]) == []


def test_missing_file_loads_as_empty(tmp_path):
    assert load_local_denylist(root=tmp_path) == []


# -- file format ----------------------------------------------------------


def test_comments_and_blank_lines_are_ignored(tmp_path):
    # Built by joining rather than one literal: an escaped newline immediately
    # before a dotted token reads as a dotted pair to the file scanner, which
    # then flags this test's own data.
    lines = ["# a comment", "", ".demo-tld   # trailing comment", "", "widget-01", ""]
    (tmp_path / LOCAL_DENYLIST_FILE).write_text("\n".join(lines))
    assert load_local_denylist(root=tmp_path) == [".demo-tld", "widget-01"]


# -- it reaches commit messages, which is the point -----------------------


def test_commit_message_scanning_uses_it(tmp_path, monkeypatch):
    """This is the category the private-TLD heuristic had to be excluded for."""
    import core.privacy_scan as ps

    monkeypatch.setattr(ps, "REPO_ROOT", tmp_path)
    (tmp_path / LOCAL_DENYLIST_FILE).write_text(".demo-tld\n")
    found = ps.commit_message_violations("fixed the resolver on core" + ".demo-tld")
    assert ("local-denylist", "core" + ".demo-tld") in found


def test_the_denylist_file_is_gitignored():
    """If it were ever committed it would publish the naming scheme."""
    import subprocess

    from core.privacy_scan import REPO_ROOT

    r = subprocess.run(
        ["git", "check-ignore", LOCAL_DENYLIST_FILE],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"{LOCAL_DENYLIST_FILE} is NOT gitignored"
