"""System configuration operations (/etc/sysctl.conf, sysrc, etc)."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server


def add_sysctl_ops(state, hosts, sysctl_config, target_hosts=None, task="all"):
    """Configure sysctl parameters per-host.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        sysctl_config: dict mapping hostname → {param: value}
            Example: {"virt-01.baar": {"net.ipv4.ip_forward": "1"}}
        target_hosts: list of Host objects to deploy to (default: all)
        task: "sysctl" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in sysctl_config:
            continue

        os_key = host.get_fact(Kernel)
        params = sysctl_config[host.name]

        # Build sysctl.conf content
        sysctl_lines = [f"{key}={value}" for key, value in params.items()]
        sysctl_content = "\n".join(sysctl_lines) + "\n"

        # Deploy /etc/sysctl.conf for all Unix-like systems
        if sysctl_lines:
            add_op(
                state,
                files.put,
                name=f"Deploy /etc/sysctl.conf on {host.name}",
                src=sysctl_content,
                dest="/etc/sysctl.conf",
                mode="0644",
                host=host,
            )

            # On FreeBSD/OpenBSD, apply immediately
            if os_key in ("FreeBSD", "OpenBSD"):
                add_op(
                    state,
                    server.shell,
                    name=f"Apply sysctl on {host.name}",
                    commands=["sysctl -f /etc/sysctl.conf"],
                    host=host,
                )


def add_sysrc_ops(state, hosts, sysrc_config, target_hosts=None, task="all"):
    """Configure FreeBSD rc.conf (sysrc) variables.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        sysrc_config: dict mapping hostname → {variable: value}
            Example: {"virt-01.baar": {"cloned_interfaces": "bridge10"}}
        target_hosts: list of Host objects to deploy to (default: all)
        task: "sysrc" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in sysrc_config:
            continue

        os_key = host.get_fact(Kernel)
        if os_key != "FreeBSD":
            continue  # sysrc is FreeBSD-only

        variables = sysrc_config[host.name]

        for var, value in variables.items():
            add_op(
                state,
                server.shell,
                name=f"Set {var}={value} on {host.name}",
                commands=[f"sysrc {var}='{value}'"],
                host=host,
            )
