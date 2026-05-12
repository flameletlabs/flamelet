"""AutoSSH reverse tunnel operations (SSH keys, config, authorized_keys, startup)."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server


def add_autossh_ops(state, hosts, autossh_config, target_hosts=None, task="all"):
    """Deploy autossh tunnel infrastructure (keys, config, startup scripts).

    Args:
        state: pyinfra State object
        hosts: Inventory object
        autossh_config: dict with structure:
            {
                "tunnel_name": {
                    "remote_host": "core.example.com",          # Gateway hostname
                    "remote_user": "autossh",                   # SSH user on gateway
                    "local_port": 2240,                         # Port to forward from remote
                    "local_target": "localhost:22",             # Local target (host:port)
                    "deploy_to": ["host1", "host2"],            # Which hosts get this tunnel
                    "private_key": "/path/to/key",              # Private key on client
                    "ssh_key_content": "base64_encoded_content" # Or include key content
                }
            }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "autossh" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        os_key = host.get_fact(Kernel)

        # Process each tunnel configuration
        for tunnel_name, tunnel_cfg in autossh_config.items():
            deploy_to = tunnel_cfg.get("deploy_to", [])

            # Skip if this host isn't in the deployment list
            if host.name not in deploy_to:
                continue

            remote_host = tunnel_cfg.get("remote_host")
            remote_user = tunnel_cfg.get("remote_user", "autossh")
            local_port = tunnel_cfg.get("local_port")
            local_target = tunnel_cfg.get("local_target")
            private_key_path = tunnel_cfg.get("private_key")
            ssh_key_content = tunnel_cfg.get("ssh_key_content")

            # Deploy SSH private key if content provided
            if ssh_key_content:
                add_op(
                    state,
                    files.put,
                    name=f"Deploy SSH key for {tunnel_name} on {host.name}",
                    src=StringIO(ssh_key_content),
                    dest=private_key_path,
                    mode="0600",
                    user="root",
                    group="wheel" if os_key == "FreeBSD" else "root",
                    host=host,
                )

            # Deploy SSH config
            ssh_config_entry = (
                f"Host {tunnel_name}\n"
                f"  HostName {remote_host}\n"
                f"  User {remote_user}\n"
                f"  Port 22\n"
                f"  IdentityFile {private_key_path}\n"
                f"  RemoteForward {local_port} {local_target}\n"
                f"  ServerAliveInterval 30\n"
                f"  ServerAliveCountMax 3\n"
            )

            add_op(
                state,
                server.shell,
                name=f"Add SSH config for {tunnel_name} on {host.name}",
                commands=[
                    f"echo '{ssh_config_entry}' >> /root/.ssh/config",
                    "sort -u /root/.ssh/config -o /root/.ssh/config",
                ],
                host=host,
            )

            # Deploy rc.local startup script
            if os_key in ("FreeBSD", "OpenBSD"):
                rc_local_content = (
                    f"#!/bin/sh\n\n"
                    f"AUTOSSH_PIDFILE=/var/run/autossh-{tunnel_name}.pid "
                    f"/usr/local/bin/autossh -M 0 -f -N {tunnel_name}\n"
                )

                add_op(
                    state,
                    files.put,
                    name=f"Deploy rc.local startup for {tunnel_name} on {host.name}",
                    src=StringIO(rc_local_content),
                    dest="/etc/rc.local",
                    mode="0755",
                    host=host,
                )

                # Start autossh immediately
                add_op(
                    state,
                    server.shell,
                    name=f"Start autossh tunnel {tunnel_name} on {host.name}",
                    commands=[
                        f"AUTOSSH_PIDFILE=/var/run/autossh-{tunnel_name}.pid "
                        f"/usr/local/bin/autossh -M 0 -f -N {tunnel_name}",
                    ],
                    host=host,
                )

            elif os_key == "Linux":
                # For Linux, create a systemd service
                systemd_service = (
                    f"[Unit]\n"
                    f"Description=AutoSSH tunnel {tunnel_name}\n"
                    f"After=network.target\n\n"
                    f"[Service]\n"
                    f"Type=simple\n"
                    f"User=root\n"
                    f"ExecStart=/usr/bin/autossh -M 0 -N -F /root/.ssh/config {tunnel_name}\n"
                    f"Restart=always\n"
                    f"RestartSec=10\n\n"
                    f"[Install]\n"
                    f"WantedBy=multi-user.target\n"
                )

                add_op(
                    state,
                    files.put,
                    name=f"Deploy systemd service for {tunnel_name} on {host.name}",
                    src=StringIO(systemd_service),
                    dest=f"/etc/systemd/system/autossh-{tunnel_name}.service",
                    mode="0644",
                    host=host,
                )

                add_op(
                    state,
                    server.shell,
                    name=f"Enable and start autossh service {tunnel_name} on {host.name}",
                    commands=[
                        f"systemctl daemon-reload",
                        f"systemctl enable autossh-{tunnel_name}.service",
                        f"systemctl start autossh-{tunnel_name}.service",
                    ],
                    host=host,
                )


def add_autossh_gateway_ops(state, hosts, gateway_config, target_hosts=None, task="all"):
    """Configure autossh gateway (core) to accept reverse tunnels.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        gateway_config: dict with structure:
            {
                "gateway_host": {
                    "authorized_keys": {
                        "user": "autossh",
                        "keys": [
                            {
                                "comment": "nas-01.pangea",
                                "public_key": "ssh-rsa AAAA..."
                            }
                        ]
                    }
                }
            }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "autossh" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in gateway_config:
            continue

        gw_cfg = gateway_config[host.name]
        auth_keys_cfg = gw_cfg.get("authorized_keys", {})
        ssh_user = auth_keys_cfg.get("user", "autossh")
        keys = auth_keys_cfg.get("keys", [])

        if not keys:
            continue

        # Create SSH directory
        add_op(
            state,
            server.shell,
            name=f"Create SSH directory for {ssh_user} on {host.name}",
            commands=[
                f"mkdir -p /home/{ssh_user}/.ssh",
                f"chmod 700 /home/{ssh_user}/.ssh",
            ],
            host=host,
        )

        # Add each public key to authorized_keys
        for key_entry in keys:
            comment = key_entry.get("comment", "autossh-key")
            public_key = key_entry.get("public_key")
            key_options = key_entry.get("options", "no-pty,no-agent-forwarding")

            if key_options:
                auth_key_line = f'{key_options} {public_key} {comment}'
            else:
                auth_key_line = f'{public_key} {comment}'

            add_op(
                state,
                server.shell,
                name=f"Add authorized key for {comment} on {host.name}",
                commands=[
                    f"echo '{auth_key_line}' >> /home/{ssh_user}/.ssh/authorized_keys",
                    f"chmod 600 /home/{ssh_user}/.ssh/authorized_keys",
                    f"chown {ssh_user}:{ssh_user} /home/{ssh_user}/.ssh/authorized_keys",
                ],
                host=host,
            )
