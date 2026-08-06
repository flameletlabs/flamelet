"""Proxmox VE hypervisor operations."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server


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
                            "ip": "10.20.0.50/24",
                            "gateway": "10.20.0.1",
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
                    "ip_address": "10.20.0.100/24",
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
            # VERIFICATION ONLY. "iface" and "type" are the only keys accepted;
            # declaring address/netmask/gateway/ports raises, because this
            # operation checks that an interface exists and never builds one.
            # Define the bridge itself with the 'debian-network' task (NETWORK
            # config attribute), which renders /etc/network/interfaces.
            "networks": [
                {
                    "iface": "vmbr0",
                    "type": "bridge",
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

        # "enabled" was read but never acted on, so a pool declared
        # enabled: False was configured anyway. Honour it.
        if not pool.get("enabled", True):
            continue

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
        net_type = net.get("type")

        if net_type == "bridge":
            _configure_bridge(state, host, net)
        elif net_type == "bond":
            _configure_bond(state, host, net)
        elif net_type == "physical":
            # Physical interfaces usually don't need configuration
            pass


# Keys that describe how to BUILD an interface rather than how to check one.
# This operation cannot apply any of them — see _reject_unapplied_keys.
_BRIDGE_UNAPPLIED = ("ports", "address", "netmask", "gateway")
_BOND_UNAPPLIED = ("slaves",)


def _reject_unapplied_keys(kind, iface, spec, unapplied):
    """Fail at plan time on any key this operation cannot honour.

    These helpers only VERIFY that an interface already exists; they do not
    build one. Accepting an address or gateway and silently not applying it is
    the worst available failure shape for hypervisor networking, because the
    operation reports success and the operator believes the bridge is
    configured. Better to refuse the config than to quietly ignore half of it.

    Writing the interface definitions is deliberately NOT done here.
    ``core/operations/debian_network.py`` (task ``debian-network``, config
    attribute ``NETWORK``) already renders /etc/network/interfaces, including
    bridge-ports. It owns that file as a whole — it emits loopback and every
    interface — so a second renderer in this module would fight it for
    ownership of the same file on the same host.
    """
    present = sorted(k for k in unapplied if spec.get(k))
    if present:
        raise ValueError(
            f"proxmox: {kind} {iface!r} declares {', '.join(present)}, which this "
            f"operation does not apply — it only verifies that an existing "
            f"interface is present. Define the interface with the "
            f"'debian-network' task (NETWORK config attribute), which renders "
            f"/etc/network/interfaces, and keep the PROXMOX networks entry to "
            f"'iface' and 'type' for verification only."
        )


def _configure_bridge(state, host, bridge_spec):
    """Verify that a Linux network bridge exists for Proxmox.

    This VERIFIES only; it does not create or configure the bridge. Any
    build-time key is rejected rather than ignored — see
    _reject_unapplied_keys for why, and for where to define the bridge instead.

    Args:
        state: pyinfra State object
        host: Target host
        bridge_spec: Bridge configuration dict
    """
    iface = bridge_spec.get("iface")
    _reject_unapplied_keys("bridge", iface, bridge_spec, _BRIDGE_UNAPPLIED)

    # Bare `ip link show` so a missing bridge FAILS the deploy. The previous
    # form ended in `|| echo 'not found'`, which always exited 0 — it printed a
    # verdict but could never fail, so it verified nothing.
    add_op(
        state,
        server.shell,
        name=f"Verify bridge {iface} exists on {host.name}",
        commands=[f"ip link show {iface}"],
        host=host,
    )


def _configure_bond(state, host, bond_spec):
    """Verify that a bonded interface exists for Proxmox.

    Verifies only; does not create or configure the bond. See
    _reject_unapplied_keys.

    Args:
        state: pyinfra State object
        host: Target host
        bond_spec: Bond configuration dict
    """
    iface = bond_spec.get("iface")
    _reject_unapplied_keys("bond", iface, bond_spec, _BOND_UNAPPLIED)

    add_op(
        state,
        server.shell,
        name=f"Verify bond {iface} exists on {host.name}",
        commands=[f"ip link show {iface}"],
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
