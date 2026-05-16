"""Package upgrade operations — refresh indexes and upgrade all installed packages."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import apk, apt, server


def add_package_update_ops(state, hosts, config=None, target_hosts=None, task="all"):
    """Refresh package indexes and upgrade all installed packages.

    OS dispatch:
      Linux/Debian-family → apt.update + apt.upgrade(auto_remove=True)
      Linux/Alpine        → apk.update + apk.upgrade
      FreeBSD             → freebsd_pkg.update + freebsd_pkg.upgrade
      OpenBSD             → pkg_add -u (server.shell)

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: unused, kept for interface compatibility
        target_hosts: list of Host objects to deploy to (default: all)
        task: task name being run
    """
    from pyinfra.facts.server import LinuxDistribution
    from pyinfra.operations.freebsd import pkg as freebsd_pkg

    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        os_key = host.get_fact(Kernel)

        if os_key == "Linux":
            distro = host.get_fact(LinuxDistribution) or {}
            distro_id = distro.get("id", "").lower()

            if distro_id == "alpine":
                add_op(state, apk.update, name=f"Update package index on {host.name}", host=host)
                add_op(state, apk.upgrade, name=f"Upgrade all packages on {host.name}", host=host)
            else:
                # Debian / Ubuntu and other apt-based distros
                add_op(state, apt.update, name=f"Update package index on {host.name}", host=host)
                add_op(
                    state,
                    apt.upgrade,
                    auto_remove=True,
                    name=f"Upgrade all packages on {host.name}",
                    host=host,
                )

        elif os_key == "FreeBSD":
            add_op(
                state, freebsd_pkg.update, name=f"Update package index on {host.name}", host=host
            )
            add_op(
                state, freebsd_pkg.upgrade, name=f"Upgrade all packages on {host.name}", host=host
            )

        elif os_key == "OpenBSD":
            add_op(
                state,
                server.shell,
                name=f"Upgrade all packages on {host.name}",
                commands=["pkg_add -u"],
                host=host,
            )
