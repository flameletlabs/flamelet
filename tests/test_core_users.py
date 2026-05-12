"""Tests for core.operations.users module."""

import pytest

from core.operations.users import BASH, SUDO_GROUP


class TestConstants:
    """Test OS-specific constants."""

    @pytest.mark.parametrize("os_key", ["Alpine", "Linux", "FreeBSD", "OpenBSD"])
    def test_bash_paths_defined(self, os_key):
        """All supported OSes have bash paths defined."""
        assert os_key in BASH
        assert BASH[os_key].startswith("/")

    @pytest.mark.parametrize("os_key", ["Alpine", "Linux", "FreeBSD", "OpenBSD"])
    def test_sudo_groups_defined(self, os_key):
        """All supported OSes have sudo group names defined."""
        assert os_key in SUDO_GROUP
        assert SUDO_GROUP[os_key] in ("sudo", "wheel")

    def test_openbsd_uses_wheel(self):
        """OpenBSD should use 'wheel' for sudo group."""
        assert SUDO_GROUP["OpenBSD"] == "wheel"

    def test_linux_uses_sudo(self):
        """Linux should use 'sudo' for sudo group."""
        assert SUDO_GROUP["Linux"] == "sudo"

    def test_freebsd_uses_wheel(self):
        """FreeBSD should use 'wheel' for sudo group."""
        assert SUDO_GROUP["FreeBSD"] == "wheel"

    def test_openbsd_bash_path(self):
        """OpenBSD bash should be at /usr/local/bin/bash."""
        assert BASH["OpenBSD"] == "/usr/local/bin/bash"

    def test_linux_bash_path(self):
        """Linux bash should be at /bin/bash."""
        assert BASH["Linux"] == "/bin/bash"

    def test_freebsd_bash_path(self):
        """FreeBSD bash should be at /usr/local/bin/bash."""
        assert BASH["FreeBSD"] == "/usr/local/bin/bash"

    def test_alpine_uses_wheel(self):
        """Alpine should use 'wheel' for sudo group."""
        assert SUDO_GROUP["Alpine"] == "wheel"

    def test_alpine_shell_path(self):
        """Alpine shell should be at /bin/sh."""
        assert BASH["Alpine"] == "/bin/sh"
