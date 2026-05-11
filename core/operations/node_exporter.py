"""Prometheus node_exporter configuration."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server
from pyinfra.facts.server import Kernel


def add_node_exporter_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Prometheus node_exporter on hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → node_exporter config
            {
                "monitoring.example.com": {
                    "listen_address": ":9100",
                    "extra_args": "--collector.textfile.directory=/var/tmp/node_exporter"
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "node_exporter" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        ne_config = config[host.name]

        listen_address = ne_config.get("listen_address", ":9100")
        extra_args = ne_config.get("extra_args", "")

        if os_key == "FreeBSD":
            _configure_node_exporter_freebsd(state, host, listen_address, extra_args)
        elif os_key == "Linux":
            _configure_node_exporter_linux(state, host, listen_address, extra_args)


def _configure_node_exporter_freebsd(state, host, listen_address, extra_args):
    """Configure node_exporter on FreeBSD via sysrc."""
    commands = [
        "sysrc node_exporter_enable=YES",
        f"sysrc node_exporter_listen_address={listen_address}",
    ]

    if extra_args:
        commands.append(f"sysrc node_exporter_args='{extra_args}'")

    commands.append("service node_exporter restart || true")

    add_op(
        state,
        server.shell,
        name=f"Configure node_exporter on {host.name}",
        commands=commands,
        host=host,
    )


def _configure_node_exporter_linux(state, host, listen_address, extra_args):
    """Configure node_exporter on Linux via systemd."""
    commands = [
        "systemctl enable prometheus-node-exporter",
    ]

    # Create systemd override if extra args are needed
    if extra_args:
        override_content = f"""[Service]
ExecStart=
ExecStart=/usr/bin/prometheus-node-exporter --web.listen-address={listen_address} {extra_args}
"""
        commands.append(
            f"mkdir -p /etc/systemd/system/prometheus-node-exporter.service.d && "
            f"cat > /etc/systemd/system/prometheus-node-exporter.service.d/override.conf << 'EOF'\n{override_content}EOF"
        )
        commands.append("systemctl daemon-reload")

    commands.append("systemctl restart prometheus-node-exporter || true")

    add_op(
        state,
        server.shell,
        name=f"Configure node_exporter on {host.name}",
        commands=commands,
        host=host,
    )
