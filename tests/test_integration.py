"""Integration tests requiring SSH to live hosts."""

import subprocess

import pytest

PYTHON = "/home/syseng/.local/share/pipx/venvs/pyinfra/bin/python3"
TENANT_RUN = "tenants/home/run.py"


@pytest.mark.integration
class TestTenantDeployment:
    """Integration tests for tenant deployment."""

    def test_dry_run_single_host_all_tasks(self):
        """Dry-run deployment to single host should succeed."""
        result = subprocess.run(
            [PYTHON, TENANT_RUN, "--dry", "--limit", "gw.example.com"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "4/4 ops ok" in result.stdout

    def test_dry_run_single_host_groups_only(self):
        """Dry-run with --task groups should execute groups task only."""
        result = subprocess.run(
            [PYTHON, TENANT_RUN, "--dry", "--limit", "gw.example.com", "--task", "groups"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "2/2 ops ok" in result.stdout

    def test_dry_run_single_host_users_only(self):
        """Dry-run with --task users should execute users task only."""
        result = subprocess.run(
            [PYTHON, TENANT_RUN, "--dry", "--limit", "gw.example.com", "--task", "users"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "2/2 ops ok" in result.stdout

    def test_dry_run_verbose(self):
        """Dry-run with verbose should show debug info."""
        result = subprocess.run(
            [PYTHON, TENANT_RUN, "--dry", "--verbose", "--limit", "gw.example.com"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "[DEBUG]" in result.stdout
        assert "Inventory:" in result.stdout

    def test_dry_run_freebsd_host(self):
        """Dry-run deployment to FreeBSD host should succeed."""
        result = subprocess.run(
            [PYTHON, TENANT_RUN, "--dry", "--limit", "hypervisor.example.com"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "4/4 ops ok" in result.stdout
