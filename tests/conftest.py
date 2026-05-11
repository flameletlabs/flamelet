"""Shared test fixtures and configuration."""

from unittest.mock import patch

import pytest
from pyinfra.api import Config, Inventory, State


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
