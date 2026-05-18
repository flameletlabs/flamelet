"""Unbound DNS resolver configuration."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server

# OS-specific configuration defaults for unbound
_OS_DEFAULTS = {
    "FreeBSD": {
        "conf_path": "/usr/local/etc/unbound/unbound.conf",
        "chroot": "/usr/local/etc/unbound",
        "directory": "/usr/local/etc/unbound",
        "pidfile": "/usr/local/etc/unbound/unbound.pid",
        "username": "unbound",
        "group": "wheel",
    },
    "OpenBSD": {
        "conf_path": "/var/unbound/etc/unbound.conf",
        "chroot": "/var/unbound",
        "directory": "/var/unbound/etc",
        "pidfile": "/var/unbound/run/unbound.pid",
        "username": "_unbound",
        "group": "wheel",
    },
    "Linux": {
        "conf_path": "/etc/unbound/unbound.conf",
        "chroot": "",
        "directory": "/etc/unbound",
        "pidfile": "/run/unbound.pid",
        "username": "unbound",
        "group": "root",
    },
}


def add_unbound_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Unbound DNS resolver on hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Unbound config
            {
                "dns.example.com": {
                    "listen_on": ["127.0.0.1", "10.0.0.2"],
                    "access_control": ["127.0.0.0/8 allow", "10.0.0.0/24 allow"],
                    "local_data": [
                        {"name": "www.example.com.", "type": "A", "value": "10.0.0.53"}
                    ],
                    "forward_zones": [
                        {"name": ".", "addrs": ["10.0.0.1", "1.1.1.1"]}
                    ]
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "unbound" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host in state.failed_hosts:
            continue
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        unbound_config = config[host.name]
        os_defaults = _OS_DEFAULTS.get(os_key, _OS_DEFAULTS["Linux"])
        content = _generate_unbound_conf(unbound_config, os_defaults)
        conf_path = os_defaults["conf_path"]

        # Write config file
        add_op(
            state,
            files.put,
            name=f"Deploy Unbound config on {host.name}",
            src=StringIO(content),
            dest=conf_path,
            mode="0644",
            user="root",
            group=os_defaults["group"],
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
        elif os_key == "OpenBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable Unbound on {host.name}",
                commands=[
                    "rcctl enable unbound",
                    "rcctl restart unbound || true",
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


def _generate_unbound_config(config):
    """Generate unbound.conf content."""
    return _generate_unbound_conf(config, _OS_DEFAULTS["Linux"])


def _generate_unbound_conf(config, os_defaults):
    """Generate unbound.conf content."""
    lines = ["server:"]
    lines.append(f'    chroot: "{os_defaults["chroot"]}"')
    lines.append(f'    directory: "{os_defaults["directory"]}"')
    lines.append(f'    pidfile: "{os_defaults["pidfile"]}"')
    lines.append(f'    username: "{os_defaults["username"]}"')
    lines.append("    do-not-query-localhost: yes")
    lines.append("    do-ip4: yes")
    lines.append("    do-ip6: no")
    lines.append("    hide-identity: yes")
    lines.append("    hide-version: yes")
    lines.append("    use-syslog: yes")
    lines.append("    access-control: 0.0.0.0/0 refuse")
    lines.append("    access-control: 127.0.0.0/8 allow")

    # Access control rules (deduplicate with base rules)
    base_rules = {"0.0.0.0/0 refuse", "127.0.0.0/8 allow"}
    for rule in config.get("access_control", []):
        if rule not in base_rules:
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
        lines.append(f'    local-data: "{name} IN {rtype} {value}"')

    # Forward zones
    if config.get("forward_zones"):
        lines.append("")
        for zone in config["forward_zones"]:
            zone_name = zone.get("name", ".")
            lines.append("forward-zone:")
            lines.append(f'    name: "{zone_name}"')
            for addr in zone.get("addrs", []):
                lines.append(f"    forward-addr: {addr}")

    return "\n".join(lines)
