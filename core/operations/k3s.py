"""Kubernetes k3s cluster operations (server/agent/configuration)."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server
from pyinfra.facts.server import Kernel


def add_k3s_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy k3s Kubernetes cluster nodes (server/agent).

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "mode": "server" | "agent",
            "server_url": "https://...:6443",  (agent only)
            "token": "K...",                   (agent only)
            "channel": "latest" | "stable",
            "install_dir": "/usr/local/bin",
            "systemd_dir": "/etc/systemd/system",
            "config": {...},                   (server config dict)
        }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "k3s" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]
        mode = spec.get("mode", "agent")
        channel = spec.get("channel", "latest")
        install_dir = spec.get("install_dir", "/usr/local/bin")
        systemd_dir = spec.get("systemd_dir", "/etc/systemd/system")

        # Install k3s via official script
        install_cmd = f"curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL={channel}"

        if mode == "server":
            # Server mode: control plane
            add_op(
                state,
                server.shell,
                name=f"Install k3s server (control plane) on {host.name}",
                commands=[
                    f"sh -c '{install_cmd} INSTALL_K3S_EXEC=\"server\" sh -'",
                    "systemctl enable k3s",
                    "systemctl start k3s",
                ],
                host=host,
            )
        else:
            # Agent mode: worker node
            server_url = spec.get("server_url")
            token = spec.get("token")
            if not server_url or not token:
                raise ValueError(f"Agent mode requires server_url and token for {host.name}")

            add_op(
                state,
                server.shell,
                name=f"Install k3s agent (worker) on {host.name}",
                commands=[
                    f"sh -c '{install_cmd} INSTALL_K3S_EXEC=\"agent\" sh -'",
                    f"sed -i 's|https://127.0.0.1:6443|{server_url}|g' /etc/rancher/k3s/k3s.yaml",
                    "systemctl enable k3s-agent",
                    "systemctl start k3s-agent",
                ],
                host=host,
            )

        # Wait for k3s API server to be ready
        add_op(
            state,
            server.shell,
            name=f"Wait for k3s API on {host.name}",
            commands=[
                "timeout 300 sh -c 'until curl -sk https://127.0.0.1:6443/healthz 2>/dev/null; do sleep 2; done'",
            ],
            host=host,
        )
