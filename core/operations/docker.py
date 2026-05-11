"""Docker and Docker Compose configuration."""

import json
from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server
from pyinfra.facts.server import Kernel


def add_docker_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Docker and Docker Compose.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Docker config
            {
                "dev.baar": {
                    "users": ["syseng", "debian"],
                    "daemon": {
                        "insecure-registries": ["registry.baar"],
                        "log-driver": "journald",
                    },
                    "storage_path": "/data",
                    "storage_dirs": ["containers", "containers/stacks"],
                    "compose_stacks": [
                        {"name": "registry", "file": "registry.yaml", "content": "..."}
                    ]
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "docker" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        docker_config = config[host.name]

        # Write daemon.json
        daemon_config = docker_config.get("daemon", {})
        if daemon_config:
            daemon_json = json.dumps(daemon_config, indent=2)
            add_op(
                state,
                files.put,
                name=f"Deploy Docker daemon.json on {host.name}",
                src=StringIO(daemon_json),
                dest="/etc/docker/daemon.json",
                mode="0644",
                user="root",
                group="root",
                host=host,
            )

            # Restart docker to apply config
            add_op(
                state,
                server.shell,
                name=f"Restart Docker daemon on {host.name}",
                commands=[
                    "systemctl restart docker || true",
                ],
                host=host,
            )

        # Create storage directories
        storage_path = docker_config.get("storage_path", "/data")
        for dirname in docker_config.get("storage_dirs", []):
            dirpath = f"{storage_path}/{dirname}"
            add_op(
                state,
                server.shell,
                name=f"Create Docker storage {dirpath} on {host.name}",
                commands=[
                    f"mkdir -p {dirpath}",
                    f"chown root:docker {dirpath}",
                    f"chmod 0755 {dirpath}",
                ],
                host=host,
            )

        # Deploy Docker Compose stacks
        for stack in docker_config.get("compose_stacks", []):
            stack_name = stack.get("name", "")
            stack_file = stack.get("file", f"{stack_name}.yaml")
            stack_content = stack.get("content", "")
            stack_path = f"{storage_path}/containers/stacks/{stack_file}"

            if stack_content:
                add_op(
                    state,
                    files.put,
                    name=f"Deploy Docker Compose stack {stack_name} on {host.name}",
                    src=StringIO(stack_content),
                    dest=stack_path,
                    mode="0644",
                    user="root",
                    group="root",
                    host=host,
                )

                # Start the stack
                add_op(
                    state,
                    server.shell,
                    name=f"Start Docker Compose stack {stack_name} on {host.name}",
                    commands=[
                        f"cd $(dirname {stack_path}) && docker compose -f {stack_file} up -d || true",
                    ],
                    host=host,
                )
