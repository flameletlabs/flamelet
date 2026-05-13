"""Service management operations (systemd, service, etc)."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import server


def add_service_ops(state, hosts, service_config, target_hosts=None, task="all"):
    """Enable and manage services.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        service_config: dict mapping hostname → {service_name: {state, enabled}}
            Example: {"server.example.com": {"sshd": {"state": "started", "enabled": True}}}
        target_hosts: list of Host objects to deploy to (default: all)
        task: "services" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in service_config:
            continue

        os_key = host.get_fact(Kernel)
        services = service_config[host.name]

        for service_name, service_cfg in services.items():
            state_action = service_cfg.get("state", "started")
            enabled = service_cfg.get("enabled", True)

            if os_key == "Linux":
                # systemd
                if enabled:
                    add_op(
                        state,
                        server.shell,
                        name=f"Enable {service_name} on {host.name}",
                        commands=[f"systemctl enable {service_name}"],
                        host=host,
                    )

                if state_action == "started":
                    add_op(
                        state,
                        server.shell,
                        name=f"Start {service_name} on {host.name}",
                        commands=[f"systemctl start {service_name}"],
                        host=host,
                    )
                elif state_action == "stopped":
                    add_op(
                        state,
                        server.shell,
                        name=f"Stop {service_name} on {host.name}",
                        commands=[f"systemctl stop {service_name}"],
                        host=host,
                    )
                elif state_action == "restarted":
                    add_op(
                        state,
                        server.shell,
                        name=f"Restart {service_name} on {host.name}",
                        commands=[f"systemctl restart {service_name}"],
                        host=host,
                    )

            elif os_key == "FreeBSD":
                # sysrc + service(8)
                if enabled:
                    add_op(
                        state,
                        server.shell,
                        name=f"Enable {service_name} on {host.name}",
                        commands=[f"sysrc {service_name}_enable=YES"],
                        host=host,
                    )

                if state_action == "started":
                    add_op(
                        state,
                        server.shell,
                        name=f"Start {service_name} on {host.name}",
                        commands=[f"service {service_name} start"],
                        host=host,
                    )
                elif state_action == "stopped":
                    add_op(
                        state,
                        server.shell,
                        name=f"Stop {service_name} on {host.name}",
                        commands=[f"service {service_name} stop"],
                        host=host,
                    )
                elif state_action == "restarted":
                    add_op(
                        state,
                        server.shell,
                        name=f"Restart {service_name} on {host.name}",
                        commands=[f"service {service_name} restart"],
                        host=host,
                    )

            elif os_key == "OpenBSD":
                # rcctl (OpenBSD service manager)
                if enabled:
                    add_op(
                        state,
                        server.shell,
                        name=f"Enable {service_name} on {host.name}",
                        commands=[f"rcctl enable {service_name}"],
                        host=host,
                    )

                if state_action == "started":
                    add_op(
                        state,
                        server.shell,
                        name=f"Start {service_name} on {host.name}",
                        commands=[f"rcctl start {service_name}"],
                        host=host,
                    )
                elif state_action == "stopped":
                    add_op(
                        state,
                        server.shell,
                        name=f"Stop {service_name} on {host.name}",
                        commands=[f"rcctl stop {service_name}"],
                        host=host,
                    )
                elif state_action == "restarted":
                    add_op(
                        state,
                        server.shell,
                        name=f"Restart {service_name} on {host.name}",
                        commands=[f"rcctl restart {service_name}"],
                        host=host,
                    )
