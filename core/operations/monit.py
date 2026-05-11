"""Monit process monitoring configuration."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server
from pyinfra.facts.server import Kernel


def add_monit_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Monit process monitoring.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Monit config
            {
                "virt.home": {
                    "daemon": 120,
                    "mmonit_url": "https://monit:pass@monit.ivomarino.com/collector",
                    "httpd_port": 2812,
                    "httpd_password": "...",
                    "checks": {
                        "system": "check system $HOST\n  ...",
                        "filesystem": "check filesystem rootfs ...",
                    }
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "monit" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        monit_config = config[host.name]
        content = _generate_monitrc(monit_config)

        # Determine monitrc path based on OS
        if os_key == "FreeBSD":
            monitrc_path = "/usr/local/etc/monitrc"
        elif os_key == "OpenBSD":
            monitrc_path = "/etc/monitrc"
        else:  # Linux
            monitrc_path = "/etc/monit/monitrc"

        # Write monitrc
        add_op(
            state,
            files.put,
            name=f"Deploy Monit config on {host.name}",
            src=StringIO(content),
            dest=monitrc_path,
            mode="0600",
            user="root",
            group="wheel" if os_key in ("OpenBSD", "FreeBSD") else "root",
            host=host,
        )

        # Enable service based on OS
        if os_key == "FreeBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable Monit on {host.name}",
                commands=[
                    "sysrc monit_enable=YES",
                    "service monit restart || true",
                ],
                host=host,
            )
        elif os_key == "Linux":
            add_op(
                state,
                server.shell,
                name=f"Enable Monit on {host.name}",
                commands=[
                    "systemctl enable monit",
                    "systemctl restart monit || true",
                ],
                host=host,
            )


def _generate_monitrc(config):
    """Generate monitrc content."""
    lines = []

    # Global settings
    daemon_interval = config.get("daemon", 120)
    lines.append(f"set daemon {daemon_interval}")
    lines.append("  with start delay 0")
    lines.append("")

    # M/Monit settings (optional)
    mmonit_url = config.get("mmonit_url")
    if mmonit_url:
        lines.append(f"set mmonit {mmonit_url}")
        lines.append("  with timeout 30 seconds")
        lines.append("")

    # HTTP daemon
    httpd_port = config.get("httpd_port", 2812)
    httpd_password = config.get("httpd_password", "")
    lines.append(f"set httpd port {httpd_port}")
    if httpd_password:
        lines.append(f"  allow admin:{httpd_password}")
    lines.append("")

    # Logging
    lines.append("set logfile syslog facility log_daemon")
    lines.append("")

    # Checks (system, filesystem, network, process, etc.)
    checks = config.get("checks", {})
    for check_type, check_content in checks.items():
        lines.append(check_content)
        lines.append("")

    return "\n".join(lines)
