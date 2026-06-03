"""FreeBSD bhyve VM operations (vm-bhyve)."""

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server


def _parse_size_bytes(size_str: str) -> int:
    """Convert size string like '20G', '512M' to bytes."""
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    s = size_str.strip().upper()
    if s[-1] in units:
        return int(s[:-1]) * units[s[-1]]
    return int(s)


def _build_vm_create_command(vm_name, vcpu, memory, disk_size, image, network_config, ssh_public_key=None):
    """Build vm create command with cloud-init network configuration and SSH key.

    Args:
        vm_name: Name of the VM
        vcpu: Number of vCPUs
        memory: Memory allocation (e.g., "4G")
        disk_size: Disk size (e.g., "20G")
        image: Path to cloud image
        network_config: Network config string (e.g., "ip=192.168.1.100/24;gateway4=192.168.1.1")
        ssh_public_key: Path to SSH public key for cloud-init injection

    Returns:
        String with complete vm create command
    """
    cmd_parts = ["vm", "create"]

    # Add size and resource flags
    cmd_parts.extend(["-s", disk_size])
    cmd_parts.extend(["-m", memory])
    cmd_parts.extend(["-c", str(vcpu)])

    # Add cloud-init flag
    cmd_parts.append("-C")

    # Add SSH public key if provided
    if ssh_public_key:
        cmd_parts.extend(["-k", ssh_public_key])

    # Add network configuration if provided
    if network_config:
        cmd_parts.extend(["-n", f'"{network_config}"'])

    # Add cloud image
    if image:
        cmd_parts.extend(["-i", image])

    # Add VM name
    cmd_parts.append(vm_name)

    return " ".join(cmd_parts)


def add_bhyve_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy and manage FreeBSD bhyve virtual machines via vm-bhyve.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "vms": [
                {
                    "name": "vm-name",
                    "vcpu": 4,
                    "memory": "4G",
                    "disk": "/vm-pool/vm-name.img",
                    "disk_size": "20G",
                    "image": "path/to/cloud-image.qcow2",
                    "network": "vm-bridge0",
                    "network_config": "ip=192.168.1.100/24;gateway4=192.168.1.1;nameservers=192.168.1.1",
                    "ssh_public_key": "path/to/ssh/key.pub",
                    "autostart": True,
                }
            ],
            "bridges": [
                {"name": "vm-bridge0", "interface": "em0"}
            ],
            "zvol_pool": "vm-pool",
        }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "bhyve" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]

        zvol_pool = spec.get("zvol_pool", "vm-pool")
        bridges = spec.get("bridges", [])
        vms = spec.get("vms", [])

        # Create virtual network bridges
        for bridge in bridges:
            bridge_name = bridge.get("name")
            interface = bridge.get("interface")

            add_op(
                state,
                server.shell,
                name=f"Create bridge {bridge_name} on {host.name}",
                commands=[
                    f"ifconfig {bridge_name} create || true",
                    f"ifconfig {bridge_name} addm {interface} || true",
                ],
                host=host,
            )

        # Create and start VMs
        autostart_vms = []
        for vm in vms:
            vm_name = vm.get("name")
            vcpu = vm.get("vcpu", 2)
            memory = vm.get("memory", "2G")
            disk_size = vm.get("disk_size", "10G")
            network = vm.get("network", "vm-bridge0")
            autostart = vm.get("autostart", True)
            image = vm.get("image")
            network_config = vm.get("network_config")
            ssh_public_key = vm.get("ssh_public_key")

            disk_path = vm.get("disk", f"{zvol_pool}/{vm_name}.img")

            # Collect autostart VMs for rc.conf configuration
            if autostart:
                autostart_vms.append(vm_name)

            # If image is provided, use vm create with cloud-init
            if image:
                create_cmd = _build_vm_create_command(vm_name, vcpu, memory, disk_size, image, network_config, ssh_public_key)
                add_op(
                    state,
                    server.shell,
                    name=f"Create VM {vm_name} with cloud-init on {host.name}",
                    commands=[
                        f"if ! vm list | grep -q '^{vm_name}'; then {create_cmd}; fi",
                    ],
                    host=host,
                )
            else:
                # Traditional disk-based VM creation
                # Create disk if it doesn't exist (new VMs)
                add_op(
                    state,
                    server.shell,
                    name=f"Create disk for VM {vm_name} on {host.name}",
                    commands=[
                        f"test -f {disk_path} || truncate -s {disk_size} {disk_path}",
                    ],
                    host=host,
                )

                # Grow disk only if needed (existing VMs, fail on shrink attempt)
                desired_bytes = _parse_size_bytes(disk_size)
                add_op(
                    state,
                    server.shell,
                    name=f"Grow disk for VM {vm_name} on {host.name}",
                    commands=[
                        f"if test -f {disk_path}; then "
                        f"current=$(stat -f '%z' {disk_path}); "
                        f"if [ {desired_bytes} -lt $current ]; then "
                        f"echo 'ERROR: disk shrink not supported: cannot reduce {disk_path} to {disk_size}' >&2; exit 1; "
                        f"elif [ {desired_bytes} -gt $current ]; then "
                        f"truncate -s {disk_size} {disk_path}; "
                        f"fi; fi",
                    ],
                    host=host,
                )

            # Configure VM settings (granular sed commands for idempotency)
            # Skip if image-based (vm create already configured these)
            if not image:
                vm_settings = [
                    ("cpu", vcpu),
                    ("memory", memory),
                    ("disk0_type", vm.get("disk_type", "ahci")),
                    ("disk0_name", disk_path),
                    ("network0_type", "virtio-net"),
                    ("network0_switch", network),
                ]

                for setting_name, setting_value in vm_settings:
                    # Convert value to string and escape special chars for sed (handle / in paths)
                    str_value = str(setting_value)
                    escaped_value = str_value.replace("/", "\\/")
                    add_op(
                        state,
                        server.shell,
                        name=f"Configure VM {vm_name} {setting_name} on {host.name}",
                        commands=[
                            f"grep -q '^{setting_name}' /zroot/vm/{vm_name}/{vm_name}.conf && "
                            f"sed -i '' 's/^{setting_name}[= \"].*$/{setting_name}=\"{escaped_value}\"/' /zroot/vm/{vm_name}/{vm_name}.conf || "
                            f"echo '{setting_name}=\"{str_value}\"' >> /zroot/vm/{vm_name}/{vm_name}.conf",
                        ],
                        host=host,
                    )

                # Restart VM (skip for config-only mode)
                if task != "bhyve-config":
                    add_op(
                        state,
                        server.shell,
                        name=f"Restart VM {vm_name} on {host.name}",
                        commands=[
                            f"vm stop {vm_name} 2>/dev/null || true",
                            "sleep 3",
                            f"vm start {vm_name}",
                        ],
                        host=host,
                    )
            elif task != "bhyve-config":
                # For image-based VMs, just ensure it's started
                add_op(
                    state,
                    server.shell,
                    name=f"Start VM {vm_name} on {host.name}",
                    commands=[
                        f"vm list | grep -q '^{vm_name}' && vm start {vm_name} 2>/dev/null || true",
                    ],
                    host=host,
                )

        # Set VM autostart list in rc.conf (idempotent)
        if autostart_vms:
            vm_list = " ".join(autostart_vms)
            add_op(
                state,
                files.line,
                name=f"Set VM autostart list on {host.name}",
                path="/etc/rc.conf",
                line="^vm_list=",
                replace=f'vm_list="{vm_list}"',
                present=True,
                host=host,
            )
