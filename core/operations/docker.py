"""Docker and Docker Compose configuration."""

import json
from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server


def add_docker_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Docker and Docker Compose.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Docker config
            {
                "docker.example.com": {
                    "users": ["syseng", "deploy"],
                    "daemon": {
                        "insecure-registries": ["registry.internal"],
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

            # Restart docker ONLY when daemon.json actually changed.
            #
            # This used to be an unconditional `systemctl restart docker`.
            # server.shell always runs -- pyinfra cannot know a shell command is
            # a no-op -- so EVERY deploy of this task bounced the Docker daemon,
            # and with it every container on the host, whether or not
            # daemon.json had changed.
            #
            # That is not a cosmetic waste. On docker.newyork it made the UPS
            # monitoring flap: restarting the nut-shim container makes upsd
            # re-run sstate_connect(), which sets ups.status to the literal
            # "WAIT" while it waits for the driver dump (nut server/sstate.c).
            # OL disappears for ~5s, and a Gatus scrape landing in that window
            # recorded a 2-minute UPS "outage" while apcupsd reported ONLINE
            # throughout. Several a day, all self-inflicted by deploys.
            #
            # Idempotence is done in the shell rather than via pyinfra
            # operation metadata so it cannot drift with the pyinfra API, and
            # so it self-heals: the marker records the config the RUNNING
            # daemon was last restarted for, so a hand-edited daemon.json is
            # still picked up on the next deploy.
            add_op(
                state,
                server.shell,
                name=f"Restart Docker daemon if daemon.json changed on {host.name}",
                commands=[
                    "sum=$(sha256sum /etc/docker/daemon.json | cut -d' ' -f1); "
                    "mark=/var/lib/flamelet/docker-daemon.sha256; "
                    'if [ ! -f "$mark" ] || [ "$(cat "$mark")" != "$sum" ]; then '
                    "  systemctl restart docker || true; "
                    '  mkdir -p /var/lib/flamelet && printf \'%s\\n\' "$sum" > "$mark"; '
                    "  echo 'docker daemon restarted (daemon.json changed)'; "
                    "else echo 'docker daemon.json unchanged, not restarting'; fi",
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
            stack_dir = stack.get("dir", "")
            stack_path = f"{storage_path}/containers/stacks/{stack_file}"

            # "dir" mode: the compose file and everything it mounts are already
            # on the host, put there by the files task. Just bring the stack up.
            #
            # Added 2026-08-06. "content" mode requires the whole compose YAML to
            # be embedded as a Python string in vars/hosts/*.py, which hides it
            # from YAML tooling and review, and gives no natural home for the
            # files a stack mounts alongside it (a Gatus config, a Caddyfile).
            # With "dir", the stack lives as real files under config/docker/<name>/
            # in the tenant, ships via FILES, and this just runs compose in place.
            if stack_dir:
                add_op(
                    state,
                    server.shell,
                    name=f"Start Docker Compose stack {stack_name} on {host.name}",
                    commands=[
                        f"cd {stack_dir} && docker compose up -d --remove-orphans",
                    ],
                    host=host,
                )
                continue

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
