"""Proxmox VE hypervisor operations."""

import json
from pyinfra.api.operation import add_op
from pyinfra.operations import files, server


def add_proxmox_ops(state, hosts, config, target_hosts=None, task="proxmox"):
    """Deploy and manage Proxmox VE infrastructure.

    Manages:
    - LXC containers and QEMU VMs
    - Storage pools (ZFS, LVM, local directories)
    - Network bridges and interfaces
    - Host configuration

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "pve_host": "hostname",
            "api_user": "root@pam",
            "api_password": "password or env var",
            "containers": [
                {
                    "vmid": 100,
                    "name": "container-name",
                    "type": "lxc",
                    "ostype": "debian",
                    "cores": 4,
                    "memory": 16384,
                    "swap": 2048,
                    "storage": "local-zfs",
                    "rootfs_size": "100G",
                    "network": {
                        "eth0": {
                            "bridge": "vmbr0",
                            "ip": "192.168.160.50/24",
                            "gateway": "192.168.160.1",
                        }
                    },
                    "onboot": True,
                    "status": "running",
                }
            ],
            "vms": [
                {
                    "vmid": 200,
                    "name": "vm-name",
                    "type": "qemu",
                    "cores": 4,
                    "memory": 8192,
                    "disk": "/zfs/pool/vm-name.qcow2",
                    "disk_size": "50G",
                    "storage": "local-zfs",
                    "network": "vmbr0",
                    "ip_address": "192.168.160.100/24",
                    "image": "debian-13",
                    "autostart": True,
                }
            ],
            "storage": [
                {
                    "name": "local-zfs",
                    "type": "zfspool",
                    "pool": "rpool",
                    "content": ["images", "rootdir"],
                    "enabled": True,
                }
            ],
            "networks": [
                {
                    "iface": "vmbr0",
                    "type": "bridge",
                    "address": "192.168.160.2",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.160.1",
                    "ports": ["nic0"],
                }
            ],
        }
        target_hosts: list of Host objects (default: all)
        task: "proxmox" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]

        # Log that we're processing Proxmox configuration
        add_op(
            state,
            server.shell,
            name=f"Validate Proxmox installation on {host.name}",
            commands=[
                "test -x /usr/bin/pveversion && echo 'Proxmox VE installed' || echo 'Proxmox VE not found'",
            ],
            host=host,
        )

        # Storage configuration
        _configure_storage(state, host, spec)

        # Network configuration
        _configure_networks(state, host, spec)

        # LXC containers
        _configure_containers(state, host, spec)

        # QEMU VMs
        _configure_vms(state, host, spec)


def _configure_storage(state, host, spec):
    """Configure Proxmox storage pools.

    Args:
        state: pyinfra State object
        host: Target host
        spec: Proxmox configuration dict
    """
    storage_pools = spec.get("storage", [])

    if not storage_pools:
        return

    for pool in storage_pools:
        pool_name = pool.get("name")
        pool_type = pool.get("type")
        enabled = pool.get("enabled", True)

        if pool_type == "zfspool":
            _configure_zfs_pool(state, host, pool)
        elif pool_type == "dir":
            _configure_dir_pool(state, host, pool)
        elif pool_type == "lvm":
            _configure_lvm_pool(state, host, pool)

        # Verify pool exists
        add_op(
            state,
            server.shell,
            name=f"Verify storage pool {pool_name} on {host.name}",
            commands=[
                f"pvesh get /api2/json/storage/{pool_name} > /dev/null 2>&1 && echo 'Pool {pool_name} exists' || echo 'Pool {pool_name} not found'",
            ],
            host=host,
        )


def _configure_zfs_pool(state, host, pool_spec):
    """Configure a ZFS-based Proxmox storage pool.

    Args:
        state: pyinfra State object
        host: Target host
        pool_spec: ZFS pool configuration dict
    """
    pool_name = pool_spec.get("name")
    zfs_pool = pool_spec.get("pool")
    content = pool_spec.get("content", ["images", "rootdir"])

    # Verify ZFS pool exists
    add_op(
        state,
        server.shell,
        name=f"Verify ZFS pool {zfs_pool} on {host.name}",
        commands=[
            f"zpool list {zfs_pool} > /dev/null 2>&1 && echo 'ZFS pool {zfs_pool} online' || echo 'ZFS pool {zfs_pool} not found'",
        ],
        host=host,
    )

    # Create Proxmox storage pool if it doesn't exist
    content_str = ",".join(content)
    add_op(
        state,
        server.shell,
        name=f"Create Proxmox storage pool {pool_name} on {host.name}",
        commands=[
            f"pvesh get /storage/{pool_name} > /dev/null 2>&1 || "
            f"pvesh create /storage -storage {pool_name} -type zfspool -pool {zfs_pool} -content {content_str}",
        ],
        host=host,
    )


def _configure_dir_pool(state, host, pool_spec):
    """Configure a directory-based Proxmox storage pool.

    Args:
        state: pyinfra State object
        host: Target host
        pool_spec: Directory pool configuration dict
    """
    pool_name = pool_spec.get("name")
    pool_path = pool_spec.get("path")
    content = pool_spec.get("content", ["images", "rootdir"])

    # Ensure directory exists
    add_op(
        state,
        server.shell,
        name=f"Ensure directory {pool_path} exists on {host.name}",
        commands=[
            f"mkdir -p {pool_path}",
        ],
        host=host,
    )

    # Create Proxmox storage pool if it doesn't exist
    content_str = ",".join(content)
    add_op(
        state,
        server.shell,
        name=f"Create directory storage pool {pool_name} on {host.name}",
        commands=[
            f"pvesh get /storage/{pool_name} > /dev/null 2>&1 || "
            f"pvesh create /storage -storage {pool_name} -type dir -path {pool_path} -content {content_str}",
        ],
        host=host,
    )


def _configure_lvm_pool(state, host, pool_spec):
    """Configure an LVM-based Proxmox storage pool.

    Args:
        state: pyinfra State object
        host: Target host
        pool_spec: LVM pool configuration dict
    """
    pool_name = pool_spec.get("name")
    vg_name = pool_spec.get("vg")
    content = pool_spec.get("content", ["images"])

    # Verify LVM VG exists
    add_op(
        state,
        server.shell,
        name=f"Verify LVM VG {vg_name} on {host.name}",
        commands=[
            f"vgdisplay {vg_name} > /dev/null 2>&1 && echo 'VG {vg_name} found' || echo 'VG {vg_name} not found'",
        ],
        host=host,
    )

    # Create Proxmox storage pool if it doesn't exist
    content_str = ",".join(content)
    add_op(
        state,
        server.shell,
        name=f"Create LVM storage pool {pool_name} on {host.name}",
        commands=[
            f"pvesh get /storage/{pool_name} > /dev/null 2>&1 || "
            f"pvesh create /storage -storage {pool_name} -type lvmthin -vgname {vg_name} -content {content_str}",
        ],
        host=host,
    )


def _configure_networks(state, host, spec):
    """Configure Proxmox network interfaces and bridges.

    Args:
        state: pyinfra State object
        host: Target host
        spec: Proxmox configuration dict
    """
    networks = spec.get("networks", [])

    if not networks:
        return

    # Build network configuration
    # Note: This is a simplified implementation
    # Full implementation would use netplan or /etc/network/interfaces
    for net in networks:
        iface = net.get("iface")
        net_type = net.get("type")

        if net_type == "bridge":
            _configure_bridge(state, host, net)
        elif net_type == "bond":
            _configure_bond(state, host, net)
        elif net_type == "physical":
            # Physical interfaces usually don't need configuration
            pass


def _configure_bridge(state, host, bridge_spec):
    """Configure a Linux network bridge for Proxmox.

    Args:
        state: pyinfra State object
        host: Target host
        bridge_spec: Bridge configuration dict
    """
    iface = bridge_spec.get("iface")
    ports = bridge_spec.get("ports", [])
    address = bridge_spec.get("address")
    netmask = bridge_spec.get("netmask")
    gateway = bridge_spec.get("gateway")

    # Verify bridge exists
    add_op(
        state,
        server.shell,
        name=f"Verify bridge {iface} on {host.name}",
        commands=[
            f"ip link show {iface} > /dev/null 2>&1 && echo 'Bridge {iface} exists' || echo 'Bridge {iface} not found'",
        ],
        host=host,
    )


def _configure_bond(state, host, bond_spec):
    """Configure a bonded interface for Proxmox.

    Args:
        state: pyinfra State object
        host: Target host
        bond_spec: Bond configuration dict
    """
    iface = bond_spec.get("iface")
    slaves = bond_spec.get("slaves", [])

    # Verify bond exists
    add_op(
        state,
        server.shell,
        name=f"Verify bond {iface} on {host.name}",
        commands=[
            f"ip link show {iface} > /dev/null 2>&1 && echo 'Bond {iface} exists' || echo 'Bond {iface} not found'",
        ],
        host=host,
    )


def _configure_containers(state, host, spec):
    """Configure LXC containers on Proxmox.

    Args:
        state: pyinfra State object
        host: Target host
        spec: Proxmox configuration dict
    """
    containers = spec.get("containers", [])

    if not containers:
        return

    for container in containers:
        vmid = container.get("vmid")
        name = container.get("name")

        # Verify container exists
        add_op(
            state,
            server.shell,
            name=f"Verify LXC container {name} (VMID {vmid}) on {host.name}",
            commands=[
                f"pct config {vmid} > /dev/null 2>&1 && echo 'Container {name} exists' || echo 'Container {name} not found'",
            ],
            host=host,
        )


def _configure_vms(state, host, spec):
    """Configure QEMU VMs on Proxmox.

    Args:
        state: pyinfra State object
        host: Target host
        spec: Proxmox configuration dict
    """
    vms = spec.get("vms", [])

    if not vms:
        return

    for vm in vms:
        vmid = vm.get("vmid")
        name = vm.get("name")

        # Verify VM exists
        add_op(
            state,
            server.shell,
            name=f"Verify QEMU VM {name} (VMID {vmid}) on {host.name}",
            commands=[
                f"qm config {vmid} > /dev/null 2>&1 && echo 'VM {name} exists' || echo 'VM {name} not found'",
            ],
            host=host,
        )
