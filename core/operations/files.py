"""Generic file operations (copy, put, template, etc)."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files


def add_file_ops(state, hosts, file_config, target_hosts=None, task="all"):
    """Deploy files from source to destination.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        file_config: dict mapping hostname → list of file specs
            Each spec: {
                "src": "/path/to/source",      # local file path
                "dest": "/path/on/host",       # remote destination
                "mode": "0644",                # (optional) file mode
                "owner": "root",               # (optional) file owner
                "group": "wheel",              # (optional) file group
            }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "files" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in file_config:
            continue

        files_list = file_config[host.name]

        for file_spec in files_list:
            src = file_spec.get("src")
            dest = file_spec.get("dest")
            mode = file_spec.get("mode")
            owner = file_spec.get("owner")
            group = file_spec.get("group")

            add_op(
                state,
                files.put,
                name=f"Deploy {dest} on {host.name}",
                src=src,
                dest=dest,
                mode=mode,
                owner=owner,
                group=group,
                host=host,
            )


def add_file_content_ops(state, hosts, content_config, target_hosts=None, task="all"):
    """Deploy file content (from string, not file path).

    Args:
        state: pyinfra State object
        hosts: Inventory object
        content_config: dict mapping hostname → {dest: content}
            Example: {
                "virt-01.baar": {
                    "/etc/custom.conf": "key=value\\nkey2=value2"
                }
            }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "files" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in content_config:
            continue

        contents = content_config[host.name]

        for dest, content in contents.items():
            add_op(
                state,
                files.put,
                name=f"Deploy {dest} on {host.name}",
                src=StringIO(content),
                dest=dest,
                mode="0644",
                host=host,
            )
