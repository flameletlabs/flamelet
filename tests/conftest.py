"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pyinfra.api import Config, State
from pyinfra.api.inventory import Inventory


@pytest.fixture
def tmp_tenant_dir():
    """Create a temporary tenant directory with mock files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tenant_path = Path(tmpdir) / "test_tenant"
        tenant_path.mkdir()

        # Create vars directory
        (tenant_path / "vars").mkdir()
        (tenant_path / "vars" / "__init__.py").write_text("""
USERS = {
    "testuser": {
        "comment": "Test User",
        "password": "$6$testpass",
        "groups": ["wheel"],
        "shell": "/bin/bash",
        "public_keys": ["ssh-rsa AAAA..."],
    }
}

GROUPS = ["wheel"]
BASH = "/bin/bash"
SUDO_GROUP = "wheel"
LUMACA_PASSWORD = "$6$testpass"
""")

        # Create all.py
        (tenant_path / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl", "git"],
    "FreeBSD": ["curl", "git"],
}

MONIT = {}
WIREGUARD = {}
""")

        # Create location and hosts subdirectories
        (tenant_path / "vars" / "location").mkdir()
        (tenant_path / "vars" / "hosts").mkdir()

        # Create inventory.py using pyinfra's actual Inventory API
        (tenant_path / "inventory.py").write_text("""
from pyinfra.api.inventory import Inventory

def build_inventory():
    return Inventory(
        (
            [
                ("test.local", {}),
                ("web.example.com", {}),
                ("db.example.com", {}),
            ],
            {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"},
        ),
        web=(["web.example.com"], {}),
        db=(["db.example.com"], {}),
    )
""")

        yield tenant_path


@pytest.fixture
def mock_inventory():
    """Create a mock pyinfra Inventory."""
    return Inventory(
        (
            [
                ("host1.local", {}),
                ("host2.local", {}),
            ],
            {"ssh_user": "syseng"},
        ),
        test=(["host1.local", "host2.local"], {}),
    )


@pytest.fixture
def mock_state(mock_inventory):
    """Create a mock pyinfra State."""
    config = Config(CONNECT_TIMEOUT=5, DRY=True)
    state = State(mock_inventory, config)
    return state


@pytest.fixture
def mock_host():
    """Create a mock pyinfra Host object."""
    host = MagicMock()
    host.name = "test.local"
    host.groups = ["test"]
    host.data = {}
    return host
