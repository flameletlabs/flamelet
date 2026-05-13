"""FreeBSD bhyve VM operations (vm-bhyve)."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server


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
                    "image": "path/to/install.iso",
                    "network": "vm-bridge0",
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

        # Initialize vm-bhyve if not already done
        add_op(
            state,
            server.shell,
            name=f"Initialize vm-bhyve on {host.name}",
            commands=[
                "pw groupadd -n vm -M 2>/dev/null || true",
                "mkdir -p /etc/vm /var/lib/vm && chown vm:vm /var/lib/vm /etc/vm",
                "echo 'vm_enable=\"YES\"' >> /etc/rc.conf.local 2>/dev/null || true",
            ],
            host=host,
        )

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
        for vm in vms:
            vm_name = vm.get("name")
            vcpu = vm.get("vcpu", 2)
            memory = vm.get("memory", "2G")
            disk_size = vm.get("disk_size", "10G")
            network = vm.get("network", "vm-bridge0")
            autostart = vm.get("autostart", True)

            disk_path = vm.get("disk", f"{zvol_pool}/{vm_name}.img")

            # Create disk
            add_op(
                state,
                server.shell,
                name=f"Create disk for VM {vm_name} on {host.name}",
                commands=[
                    f"truncate -s {disk_size} {disk_path} || true",
                ],
                host=host,
            )

            # Create VM config
            vm_config = f"""cpu {vcpu}
memory {memory}
disk0_type=ahci
disk0_name={disk_path}
network0_type=virtio-net
network0_switch={network}
"""

            add_op(
                state,
                files.put,
                name=f"Configure VM {vm_name} on {host.name}",
                src=StringIO(vm_config.strip()),
                dest=f"/etc/vm/{vm_name}.conf",
                user="vm",
                group="vm",
                mode="0644",
                host=host,
            )

            # Start VM
            add_op(
                state,
                server.shell,
                name=f"Start VM {vm_name} on {host.name}",
                commands=[
                    f"bhyvectl --vm={vm_name} --destroy 2>/dev/null || true",
                    f"bhyve -A -H -P -s 0:0,hostbridge -s 1,lpc -s 2:0,virtio-net,{network} "
                    f"-s 3:0,ahci,{disk_path} -c {vcpu} -m {memory} -w {vm_name} || true",
                ],
                host=host,
            )

            if autostart:
                add_op(
                    state,
                    server.shell,
                    name=f"Enable autostart for VM {vm_name} on {host.name}",
                    commands=[
                        f"echo '{vm_name}' >> /etc/vm/autostart 2>/dev/null || true",
                    ],
                    host=host,
                )
