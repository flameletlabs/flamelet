"""Monit process monitoring configuration."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server


def add_monit_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Monit process monitoring.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Monit config
            {
                "monitor.example.com": {
                    "daemon": 120,
                    "mmonit_url": "https://monit:monit-password@mmonit.example.com/collector",
                    "httpd_port": 2812,
                    "httpd_password": "monit-web-password",
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

        # Determine monitrc path based on OS
        if os_key == "FreeBSD":
            monitrc_path = "/usr/local/etc/monitrc"
        elif os_key == "OpenBSD":
            monitrc_path = "/etc/monitrc"
        else:  # Linux
            monitrc_path = "/etc/monit/monitrc"

        # State directory, per-OS. This used to be hardcoded to /var/lib/monit
        # in the rendered config while the directory was only CREATED on Linux,
        # so on OpenBSD monit was handed idfile/statefile paths under a
        # directory that does not exist and never would. The BSDs use
        # /var/monit, which is where core.london's existing id and state already
        # live -- deploying the hardcoded version would also have orphaned the
        # instance id monit has carried since 2023.
        state_dir = "/var/monit" if os_key in ("OpenBSD", "FreeBSD") else "/var/lib/monit"
        content = _generate_monitrc(monit_config, state_dir=state_dir)

        add_op(
            state,
            files.directory,
            name=f"Create monit state directory on {host.name}",
            path=state_dir,
            user="root",
            group="wheel" if os_key in ("OpenBSD", "FreeBSD") else "root",
            mode="0755",
            host=host,
        )

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
        elif os_key == "OpenBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable Monit on {host.name}",
                commands=[
                    "rcctl enable monit",
                    "rcctl restart monit || true",
                ],
                host=host,
            )


def _generate_monit_config(config, hostname=None):
    """Generate monit config."""
    return _generate_monitrc(config)


def _generate_monitrc(config, state_dir="/var/lib/monit"):
    """Generate monitrc content.

    state_dir defaults to the Linux location for backwards compatibility; the
    caller passes /var/monit on the BSDs, which is where monit already keeps
    its id and state there.
    """
    lines = []

    # Global settings
    daemon_interval = config.get("daemon", 120)
    lines.append(f"set daemon {daemon_interval}")
    lines.append("  with start delay 0")
    lines.append("")

    # State files kept off /root, which is read-only on some hosts (Proxmox).
    lines.append(f"set idfile {state_dir}/monit.id")
    lines.append(f"set statefile {state_dir}/monit.state")
    lines.append("")

    # M/Monit settings (optional)
    mmonit_url = config.get("mmonit_url")
    if mmonit_url:
        lines.append(f"set mmonit {mmonit_url}")
        lines.append("  with timeout 30 seconds")
        hostgroup = config.get("mmonit_hostgroup")
        if hostgroup:
            lines.append(f'  with hostgroups [ "{hostgroup}" ]')
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
