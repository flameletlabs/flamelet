"""User and group management operations (tenant-agnostic).

Supported OS: Alpine, Debian, FreeBSD, OpenBSD
"""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import server

# OS-specific config: Alpine, Debian, FreeBSD, OpenBSD
BASH = {
    "Alpine":  "/bin/sh",
    "Linux":   "/bin/bash",
    "FreeBSD": "/usr/local/bin/bash",
    "OpenBSD": "/usr/local/bin/bash",
}
SUDO_GROUP = {
    "Alpine":  "wheel",
    "Linux":   "sudo",
    "FreeBSD": "wheel",
    "OpenBSD": "wheel",
}


def add_groups(state, hosts, group_names):
    """Create system groups on specified hosts.

    Args:
        state: pyinfra State object
        hosts: list of Host objects
        group_names: list of group names to create (required, provided by tenant vars)
    """
    for host in hosts:
        for group_name in group_names:
            add_op(
                state,
                server.group,
                name=f"Group {group_name} on {host.name}",
                group=group_name,
                host=host,
            )


def add_users(state, hosts, users_config):
    """Create system users with SSH keys on specified hosts.

    Args:
        state: pyinfra State object
        hosts: list of Host objects
        users_config: dict mapping user name -> {
            'password': str,
            'groups': [str],
            'shell': str,
            'public_keys': [str],
            'comment': str,
        }
    """
    for host in hosts:
        os_key = host.get_fact(Kernel)

        for user_name, user_cfg in users_config.items():
            # Resolve dynamic shell path
            shell = user_cfg.get("shell")
            if isinstance(shell, dict):
                shell = shell.get(os_key, "/bin/sh")

            # Resolve dynamic sudo group
            groups = user_cfg.get("groups", [])
            if isinstance(groups, dict):
                groups = [groups.get(os_key, "")] if groups.get(os_key) else []

            add_op(
                state,
                server.user,
                name=f"User {user_name} on {host.name}",
                user=user_name,
                comment=user_cfg.get("comment", ""),
                password=user_cfg.get("password"),
                groups=groups,
                append=True,
                shell=shell,
                public_keys=user_cfg.get("public_keys", []),
                ensure_home=True,
                host=host,
            )


def add_user_ops(state, inventory, users_config, group_names, target_hosts=None, task="all"):
    """Add user/group management operations for specified hosts.

    Args:
        state: pyinfra State object
        inventory: pyinfra Inventory object
        users_config: dict of user configurations (see add_users)
        group_names: list of group names to create (required, from tenant vars)
        target_hosts: list of Host objects to deploy to (default: all hosts)
        task: "groups", "users", or "all" (default: "all")
    """
    hosts = target_hosts if target_hosts else list(inventory)

    if task in ("groups", "all"):
        add_groups(state, hosts, group_names)
    if task in ("users", "all"):
        add_users(state, hosts, users_config)
