"""The commit-message layer of the privacy guard.

Exists because an address reached this repository's public history through a
commit message on 2026-08-12 while both existing layers reported clean: they
scan file content, and a message is not a file.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from core.privacy_scan import COMMIT_MSG_CHECKS, commit_message_violations

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "scripts" / "commit_msg_privacy_scan.py"


def names(msg):
    return {c for c, _ in commit_message_violations(msg)}


# -- what must be caught --------------------------------------------------


def test_site_subnet_is_caught():
    """A third octet outside the consumer-router defaults is a real network."""
    assert "private-ipv4" in names("moved the host to " + "192.168." + "30.4 today")


def test_tailscale_node_name_is_caught():
    assert "ts-net-hostname" in names("peer " + "virt-01-site" + ".ts" + ".net flapped")


def test_home_path_is_caught():
    assert "home-path" in names("config now at " + "/home/" + "syseng/.config/thing")


def test_private_key_is_caught():
    assert "secret" in names("-----BEGIN " + "RSA PRIVATE" + " KEY-----")


# -- what must NOT be caught ---------------------------------------------


# Tokens are split so this file does not trip the FILE layer on its own test
# data -- the same convention core/privacy_scan.py uses for its self-test
# samples. That the file layer catches them here is the guard working.
@pytest.mark.parametrize(
    "msg",
    [
        "call " + "subprocess" + ".run instead of " + "os" + ".system",
        "pytest" + ".ini now sets testpaths",
        "read " + "pyinfra" + ".facts" + ".server for the Kernel fact",
        "vite" + ".config gains a proxy entry",
        "bumped the address to " + "192.168." + "1.1 on the lab router",
        "documentation addresses " + "192.0." + "2.5 and " + "203.0." + "113.9 are fine",
    ],
)
def test_ordinary_technical_prose_is_not_flagged(msg):
    """A guard that cries wolf gets widened until it stops guarding.

    Dotted identifiers are ordinary in commit messages, and 192.168.0/1.x are
    ubiquitous router defaults that carry no information about anyone's network.
    """
    assert commit_message_violations(msg) == []


def test_private_tld_check_is_deliberately_excluded():
    """Documented limitation, asserted so nobody 'fixes' it by accident.

    `word.word` matches ordinary prose; measured over this repo's own history it
    produced ~30 false positives and no unique true ones.
    """
    assert "private-tld-hostname" not in COMMIT_MSG_CHECKS


# -- the hook itself ------------------------------------------------------


def run_hook(tmp_path, message):
    f = tmp_path / "COMMIT_EDITMSG"
    f.write_text(message)
    return subprocess.run([sys.executable, str(HOOK), str(f)], capture_output=True, text=True)


def test_hook_passes_a_clean_message(tmp_path):
    assert run_hook(tmp_path, "api: add a driver hook\n\nNothing private here.\n").returncode == 0


def test_hook_blocks_and_names_the_match(tmp_path):
    r = run_hook(tmp_path, "fix: move to " + "192.168." + "30.4\n")
    assert r.returncode == 1
    assert "private-ipv4" in r.stderr
    assert "COMMIT BLOCKED" in r.stderr


def test_hook_ignores_git_comment_lines(tmp_path):
    """git strips these before storing, so they cannot leak.

    Scanning them would flag the diff git helpfully includes in the template.
    """
    msg = "docs: tidy\n\n# On branch main\n# " + "192.168." + "30.4 appears in the diff\n"
    assert run_hook(tmp_path, msg).returncode == 0
