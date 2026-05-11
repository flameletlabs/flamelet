"""Sudoers configuration operations (tenant-agnostic)."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files


def add_sudoers_ops(state, inventory, users_config, target_hosts=None, task="all"):
    """Configure NOPASSWD sudoers entries for specified users on Linux hosts with _sudo.

    Writes /etc/sudoers.d/<user> for each user in users_config on Linux hosts
    configured with _sudo: True. BSD hosts with wheel group don't need this.
    Hosts with _doas (OpenBSD) don't use sudoers at all.

    Args:
        state: pyinfra State object
        inventory: pyinfra Inventory object
        users_config: dict mapping user name -> config (same shape as add_user_ops)
        target_hosts: list of Host objects to deploy to (default: all hosts)
        task: "sudo" or "all"
    """
    hosts = target_hosts if target_hosts else list(inventory)

    for host in hosts:
        # Only apply to Linux hosts with _sudo configured
        if host.get_fact(Kernel) != "Linux" or not host.data.get("_sudo"):
            continue

        for user_name in users_config:
            add_op(
                state,
                files.put,
                name=f"Sudoers NOPASSWD for {user_name} on {host.name}",
                src=StringIO(f"{user_name} ALL=(ALL) NOPASSWD:ALL\n"),
                dest=f"/etc/sudoers.d/{user_name}",
                mode="0440",
                host=host,
            )
