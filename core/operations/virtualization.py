"""FreeBSD virtualization operations (vm-bhyve VMs and Bastille jails)."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server, files
from pyinfra.facts.server import Kernel


def add_virtualization_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy and manage FreeBSD virtual machines and jails.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "type": "bhyve" | "jail",
            "vms": [                  (bhyve only)
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
            "jails": [                (jail only)
                {
                    "name": "jail-name",
                    "ip": "192.168.1.100",
                    "host": "jail.example.com",
                    "path": "/jails/jail-name",
                    "packages": ["pkg", "bash"],
                    "autostart": True,
                }
            ],
            "bridges": [              (bhyve only)
                {"name": "vm-bridge0", "interface": "em0"}
            ],
            "zvol_pool": "vm-pool",   (bhyve only)
        }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "virtualization" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]
        os_key = host.get_fact(Kernel)

        # Only support FreeBSD for now
        if os_key != "FreeBSD":
            continue

        vtype = spec.get("type", "bhyve")

        if vtype == "bhyve":
            _add_bhyve_ops(state, host, spec)
        elif vtype == "jail":
            _add_jail_ops(state, host, spec)


def _add_bhyve_ops(state, host, spec):
    """Add vm-bhyve virtual machine operations."""
    zvol_pool = spec.get("zvol_pool", "vm-pool")
    bridges = spec.get("bridges", [])
    vms = spec.get("vms", [])

    # Initialize vm-bhyve if not already done
    add_op(
        state,
        server.shell,
        name=f"Initialize vm-bhyve on {host.name}",
        commands=[
            f"pw groupadd -n vm -M 2>/dev/null || true",
            f"mkdir -p /etc/vm /var/lib/vm && chown vm:vm /var/lib/vm /etc/vm",
            f"echo 'vm_enable=\"YES\"' >> /etc/rc.conf.local 2>/dev/null || true",
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
        vm_config = f"""
cpu {vcpu}
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
            src=vm_config.strip(),
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


def _add_jail_ops(state, host, spec):
    """Add Bastille jail operations."""
    jails = spec.get("jails", [])

    # Install bastille if not present
    add_op(
        state,
        server.shell,
        name=f"Ensure bastille installed on {host.name}",
        commands=[
            "pkg install -y bastille 2>/dev/null || true",
        ],
        host=host,
    )

    # Create and configure jails
    for jail in jails:
        jail_name = jail.get("name")
        ip_addr = jail.get("ip")
        jail_host = jail.get("host", jail_name)
        jail_path = jail.get("path", f"/jails/{jail_name}")
        packages = jail.get("packages", [])
        autostart = jail.get("autostart", True)

        # Create jail
        add_op(
            state,
            server.shell,
            name=f"Create Bastille jail {jail_name} on {host.name}",
            commands=[
                f"bastille create {jail_name} 13.2-RELEASE {ip_addr} 2>/dev/null || true",
            ],
            host=host,
        )

        # Set hostname
        add_op(
            state,
            server.shell,
            name=f"Set hostname for jail {jail_name} on {host.name}",
            commands=[
                f"echo '{jail_host}' > {jail_path}/root/etc/hostname",
            ],
            host=host,
        )

        # Install packages in jail
        for package in packages:
            add_op(
                state,
                server.shell,
                name=f"Install {package} in jail {jail_name} on {host.name}",
                commands=[
                    f"bastille pkg {jail_name} install -y {package}",
                ],
                host=host,
            )

        # Start jail
        add_op(
            state,
            server.shell,
            name=f"Start jail {jail_name} on {host.name}",
            commands=[
                f"bastille start {jail_name} || true",
            ],
            host=host,
        )

        if autostart:
            add_op(
                state,
                server.shell,
                name=f"Enable autostart for jail {jail_name} on {host.name}",
                commands=[
                    f"sed -i '' 's/{jail_name}.*enabled.*0/{jail_name} {{\\'  enabled \\' = \\'1\\' }}/' /etc/bastille/bastille.conf || true",
                ],
                host=host,
            )
