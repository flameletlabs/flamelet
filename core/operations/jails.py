"""FreeBSD Bastille jail operations."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server


def add_jail_ops(state, hosts, config, target_hosts=None, task="all"):
    """Manage FreeBSD Bastille jails.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "jails": [
                {
                    "name": "jail-name",
                    "ip": "192.168.1.100",
                    "host": "jail.example.com",
                    "path": "/jails/jail-name",
                    "packages": ["pkg", "bash"],
                    "autostart": True,
                }
            ]
        }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "jails" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]
        jails = spec.get("jails", [])

        # Install bastille if not present
        add_op(
            state,
            server.shell,
            name=f"Ensure bastille installed on {host.name}",
            commands=[
                "pkg install -y bastille 2>/dev/null || true",
            ],
            host=host,
        )

        # Create and configure jails
        for jail in jails:
            jail_name = jail.get("name")
            ip_addr = jail.get("ip")
            jail_host = jail.get("host", jail_name)
            jail_path = jail.get("path", f"/jails/{jail_name}")
            packages = jail.get("packages", [])
            autostart = jail.get("autostart", True)

            # Create jail
            add_op(
                state,
                server.shell,
                name=f"Create Bastille jail {jail_name} on {host.name}",
                commands=[
                    f"bastille create {jail_name} 13.2-RELEASE {ip_addr} 2>/dev/null || true",
                ],
                host=host,
            )

            # Set hostname
            add_op(
                state,
                server.shell,
                name=f"Set hostname for jail {jail_name} on {host.name}",
                commands=[
                    f"echo '{jail_host}' > {jail_path}/root/etc/hostname",
                ],
                host=host,
            )

            # Install packages in jail
            for package in packages:
                add_op(
                    state,
                    server.shell,
                    name=f"Install {package} in jail {jail_name} on {host.name}",
                    commands=[
                        f"bastille pkg {jail_name} install -y {package}",
                    ],
                    host=host,
                )

            # Start jail
            add_op(
                state,
                server.shell,
                name=f"Start jail {jail_name} on {host.name}",
                commands=[
                    f"bastille start {jail_name} || true",
                ],
                host=host,
            )

            if autostart:
                add_op(
                    state,
                    server.shell,
                    name=f"Enable autostart for jail {jail_name} on {host.name}",
                    commands=[
                        f"sed -i '' 's/{jail_name}.*enabled.*0/{jail_name} {{\\'  enabled \\' = \\'1\\' }}/' /etc/bastille/bastille.conf || true",
                    ],
                    host=host,
                )
