"""pf firewall configuration (OpenBSD/FreeBSD)."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server


def add_pf_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure pf firewall on OpenBSD/FreeBSD hosts.

    Handles OS-specific differences:
    - FreeBSD: enables via sysrc (rc.conf)
    - OpenBSD: enables via rcctl

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → pf config
            {
                "firewall.example.com": {
                    "rules": "# verbatim pf.conf content\npass in proto tcp to port { 22, 80, 443 }",
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "pf" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        if os_key not in ("OpenBSD", "FreeBSD"):
            # pf is OpenBSD/FreeBSD only
            continue

        pf_config = config[host.name]
        rules = pf_config.get("rules", "")

        # Write pf.conf
        add_op(
            state,
            files.put,
            name=f"Deploy pf firewall config on {host.name}",
            src=StringIO(rules),
            dest="/etc/pf.conf",
            mode="0644",
            user="root",
            group="wheel",
            host=host,
        )

        # Validate pf rules syntax before reloading
        add_op(
            state,
            server.shell,
            name=f"Validate pf rules on {host.name}",
            commands=[
                "/sbin/pfctl -nf /etc/pf.conf",
            ],
            host=host,
        )

        # Reload pf rules (only if validation passed)
        add_op(
            state,
            server.shell,
            name=f"Reload pf rules on {host.name}",
            commands=[
                "/sbin/pfctl -f /etc/pf.conf",
            ],
            host=host,
        )

        # Enable pf on FreeBSD vs OpenBSD (different service management)
        if os_key == "FreeBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable pf on {host.name}",
                commands=[
                    "sysrc pf_enable=YES",
                    "sysrc pf_rules=/etc/pf.conf",
                ],
                host=host,
            )
        elif os_key == "OpenBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable pf on {host.name}",
                commands=[
                    "rcctl enable pf",
                    "rcctl start pf",
                ],
                host=host,
            )
