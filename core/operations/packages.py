"""Package management operations (Debian, FreeBSD, OpenBSD)."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import apt, pkg


def add_package_ops(state, hosts, packages_config, target_hosts=None, task="all"):
    """Install packages via OS-specific package manager.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        packages_config: dict mapping OS → list of package names
            Example: {"Linux": ["vim", "git"], "FreeBSD": ["vim", "git"]}
        target_hosts: list of Host objects to deploy to (default: all)
        task: "packages" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        os_key = host.get_fact(Kernel)
        pkg_list = packages_config.get(os_key, [])

        if not pkg_list:
            continue

        if os_key == "Linux":
            # Debian/Ubuntu/Alpine
            for pkg_name in pkg_list:
                add_op(
                    state,
                    apt.packages,
                    name=f"Install {pkg_name} on {host.name}",
                    packages=[pkg_name],
                    host=host,
                )

        elif os_key == "FreeBSD":
            # FreeBSD
            for pkg_name in pkg_list:
                add_op(
                    state,
                    pkg.packages,
                    name=f"Install {pkg_name} on {host.name}",
                    packages=[pkg_name],
                    host=host,
                )

        elif os_key == "OpenBSD":
            # OpenBSD: pkg_add
            # Note: pyinfra doesn't have native pkg_add support yet
            # Use server.shell as workaround
            from pyinfra.operations import server

            for pkg_name in pkg_list:
                add_op(
                    state,
                    server.shell,
                    name=f"Install {pkg_name} on {host.name}",
                    commands=[f"pkg_add -I {pkg_name}"],
                    host=host,
                )
