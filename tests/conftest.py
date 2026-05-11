"""Shared test fixtures and configuration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pyinfra.api import Config, Inventory, State


def pytest_configure(config):
    """Set FRAMEWORK_ROOT for tenant integration tests."""
    if "FRAMEWORK_ROOT" not in os.environ:
        # Framework root is 2 directories up from tests/
        framework_root = Path(__file__).parent.parent
        os.environ["FRAMEWORK_ROOT"] = str(framework_root)


@pytest.fixture
def mock_inventory():
    """Create a simple test inventory with 2 hosts."""
    return Inventory(
        (
            [
                ("test-openbsd", {"_doas": True}),
                ("test-freebsd", {}),
            ],
            {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"},
        ),
    )


@pytest.fixture
def mock_state(mock_inventory):
    """Create a State object with mock inventory."""
    config = Config()
    return State(mock_inventory, config)


@pytest.fixture(params=["Linux", "FreeBSD", "OpenBSD"])
def patch_kernel(request):
    """Parametrized fixture to patch get_fact(Kernel) for each OS."""
    os_name = request.param
    with patch("pyinfra.api.host.Host.get_fact") as mock_fact:
        mock_fact.return_value = os_name
        yield os_name
