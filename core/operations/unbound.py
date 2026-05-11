"""Unbound DNS resolver configuration."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server
from pyinfra.facts.server import Kernel


def add_unbound_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Unbound DNS resolver on hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Unbound config
            {
                "virt.home": {
                    "listen_on": ["127.0.0.1", "192.168.150.2"],
                    "access_control": ["127.0.0.0/8 allow", "192.168.150.0/24 allow"],
                    "local_data": [
                        {"name": "docker.home.", "type": "A", "value": "192.168.150.53"}
                    ],
                    "forward_zones": [
                        {"name": ".", "addrs": ["192.168.150.1", "1.1.1.1"]}
                    ]
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "unbound" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        unbound_config = config[host.name]
        content = _generate_unbound_conf(unbound_config)

        # Determine config path based on OS
        if os_key == "FreeBSD":
            conf_path = "/usr/local/etc/unbound/unbound.conf"
        elif os_key == "OpenBSD":
            conf_path = "/etc/unbound/unbound.conf"
        else:  # Linux
            conf_path = "/etc/unbound/unbound.conf"

        # Write config file
        add_op(
            state,
            files.put,
            name=f"Deploy Unbound config on {host.name}",
            src=StringIO(content),
            dest=conf_path,
            mode="0644",
            owner="root",
            group="wheel" if os_key in ("OpenBSD", "FreeBSD") else "root",
            host=host,
        )

        # Enable service based on OS
        if os_key == "FreeBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable Unbound on {host.name}",
                commands=[
                    "sysrc unbound_enable=YES",
                    "service unbound restart || true",
                ],
                host=host,
            )
        elif os_key == "Linux":
            add_op(
                state,
                server.shell,
                name=f"Enable Unbound on {host.name}",
                commands=[
                    "systemctl enable unbound",
                    "systemctl restart unbound || true",
                ],
                host=host,
            )


def _generate_unbound_conf(config):
    """Generate unbound.conf content."""
    lines = ["server:"]
    lines.append("    chroot: \"\"")
    lines.append("    pidfile: /var/run/unbound.pid")
    lines.append("    directory: /var/unbound")
    lines.append("    do-not-query-localhost: yes")
    lines.append("    do-ip4: yes")
    lines.append("    do-ip6: no")
    lines.append("    hide-identity: yes")
    lines.append("    hide-version: yes")
    lines.append("    use-syslog: yes")
    lines.append("    access-control: 0.0.0.0/0 refuse")
    lines.append("    access-control: 127.0.0.0/8 allow")

    # Access control rules
    for rule in config.get("access_control", []):
        lines.append(f"    access-control: {rule}")

    # Listen addresses
    listen_on = config.get("listen_on", ["127.0.0.1"])
    for addr in listen_on:
        lines.append(f"    interface: {addr}")

    # Local data (A records, CNAME, etc.)
    for entry in config.get("local_data", []):
        name = entry.get("name", "")
        rtype = entry.get("type", "A")
        value = entry.get("value", "")
        lines.append(f"    local-data: \"{name} IN {rtype} {value}\"")

    # Forward zones
    if config.get("forward_zones"):
        lines.append("")
        for zone in config["forward_zones"]:
            zone_name = zone.get("name", ".")
            lines.append(f"forward-zone:")
            lines.append(f"    name: \"{zone_name}\"")
            for addr in zone.get("addrs", []):
                lines.append(f"    forward-addr: {addr}")

    return "\n".join(lines)
