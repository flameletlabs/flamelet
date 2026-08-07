"""Tests for the pre-commit privacy hook.

The hook is the layer that stops a leak entering history at all — CI only sees
it once the commit object already exists, at which point sanitizing the tip no
longer removes the hostname from the commit that introduced it.

These run the real hook against a real throwaway git repository rather than
mocking git, because the behaviour that matters is what it does with STAGED
content, and staged content is exactly what a mock would have to invent.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "pre_commit_privacy_scan.py"


@pytest.fixture
def repo(tmp_path):
    """A throwaway git repo with the hook wired in via core.hooksPath."""

    def run(*a):
        return subprocess.run(a, cwd=tmp_path, capture_output=True, text=True)

    run("git", "init", "-q")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    (hooks / "pre-commit").write_text(f'#!/bin/sh\nexec "{sys.executable}" "{HOOK}"\n')
    (hooks / "pre-commit").chmod(0o755)
    run("git", "config", "core.hooksPath", ".githooks")
    # the hook resolves its imports from the real repo, so scanning logic is shared
    return tmp_path


def commit(repo, filename, content, extra=()):
    (repo / filename).parent.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(content)
    subprocess.run(["git", "add", filename], cwd=repo, capture_output=True)
    return subprocess.run(
        ["git", "commit", "-m", "probe", *extra], cwd=repo, capture_output=True, text=True
    )


class TestHookBlocksLeaks:
    def test_private_hostname_blocks_the_commit(self, repo):
        r = commit(repo, "leak.py", '"""host: gateway' + '.home"""\n')
        assert r.returncode != 0, "the commit should have been rejected"
        assert "COMMIT BLOCKED" in r.stderr
        assert "gateway" + ".home" in r.stderr, "the message must name the token"
        assert "leak.py" in r.stderr, "the message must name the file"

    def test_message_says_how_to_bypass(self, repo):
        r = commit(repo, "leak.py", '"""host: gateway' + '.home"""\n')
        assert "--no-verify" in r.stderr

    def test_private_subnet_blocks_the_commit(self, repo):
        r = commit(repo, "net.py", '"""gateway at 192.168.' + '150.2"""\n')
        assert r.returncode != 0
        assert "COMMIT BLOCKED" in r.stderr


class TestHookAllowsLegitimateContent:
    def test_clean_content_commits(self, repo):
        r = commit(repo, "ok.py", '"""host: gateway.example.com, net 10.0.0.0/24"""\n')
        assert r.returncode == 0, r.stderr

    def test_exempt_tree_is_skipped(self, repo):
        """The example tenant is deliberately fictional; generic addresses there
        are the point, so it must not be scanned."""
        r = commit(repo, "tenants/flamelet-example/x.py", '"""gateway' + '.home"""\n')
        assert r.returncode == 0, r.stderr

    def test_binary_file_does_not_crash_the_hook(self, repo):
        (repo / "blob.bin").write_bytes(bytes(range(256)) * 4)
        subprocess.run(["git", "add", "blob.bin"], cwd=repo, capture_output=True)
        r = subprocess.run(["git", "commit", "-m", "bin"], cwd=repo, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def test_no_verify_bypasses(self, repo):
        r = commit(repo, "leak.py", '"""gateway' + '.home"""\n', extra=("--no-verify",))
        assert r.returncode == 0, r.stderr


class TestHookScansStagedNotWorkingTree:
    def test_a_leak_added_after_staging_is_not_scanned(self, repo):
        """The hook checks the STAGED blob, which is what the commit contains.
        Editing a file after `git add` leaves the leak out of the commit, and
        the hook correctly lets it through — CI is the backstop for the case
        where it is staged later."""
        (repo / "f.py").write_text('"""clean: gateway.example.com"""\n')
        subprocess.run(["git", "add", "f.py"], cwd=repo, capture_output=True)
        (repo / "f.py").write_text('"""dirty: gateway' + '.home"""\n')  # unstaged
        r = subprocess.run(
            ["git", "commit", "-m", "staged-clean"], cwd=repo, capture_output=True, text=True
        )
        assert r.returncode == 0, r.stderr

    def test_the_same_leak_once_staged_is_blocked(self, repo):
        """Control for the test above: the hook is not simply ignoring the file."""
        r = commit(repo, "f.py", '"""dirty: gateway' + '.home"""\n')
        assert r.returncode != 0


class TestSharedDetection:
    def test_hook_and_ci_guard_use_the_same_module(self):
        """Two copies of these patterns would drift, and the drifted copy would
        be the one reporting CLEAN."""
        hook_src = HOOK.read_text()
        guard_src = (REPO_ROOT / "tests/unit/test_no_private_infrastructure.py").read_text()
        assert "from core.privacy_scan import" in hook_src
        assert "from core.privacy_scan import" in guard_src
