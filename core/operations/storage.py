"""Storage operations (ZFS pools, datasets, snapshots, NFS/SMB exports)."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server
from pyinfra.facts.server import Kernel


def add_storage_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy and manage ZFS storage infrastructure.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → {
            "pools": [
                {
                    "name": "pool-name",
                    "devices": ["/dev/da0", "/dev/da1"],
                    "type": "raidz1" | "raidz2" | "mirror",
                    "ashift": 12,
                    "autotrim": True,
                    "compression": "lz4",
                }
            ],
            "datasets": [
                {
                    "pool": "pool-name",
                    "name": "data/media",
                    "mountpoint": "/mnt/media",
                    "quota": "2T",
                    "compression": "lz4",
                    "nfs_share": True,
                    "smb_share": False,
                }
            ],
            "snapshots": [
                {
                    "dataset": "pool-name/data",
                    "name": "daily",
                    "recursive": True,
                    "schedule": "0 2 * * *",
                }
            ],
            "nfs_config": {
                "exports": [
                    {
                        "dataset": "pool-name/data",
                        "clients": ["10.0.0.0/24"],
                        "options": "ro,no_root_squash",
                    }
                ]
            },
            "samba_config": {
                "shares": [
                    {
                        "dataset": "pool-name/media",
                        "name": "media",
                        "comment": "Shared media",
                        "path": "/mnt/media",
                        "permissions": "public",
                    }
                ]
            }
        }
        target_hosts: list of Host objects to deploy to (default: all)
        task: "storage" or "all" (for compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]
        os_key = host.get_fact(Kernel)

        # Support FreeBSD and Linux with ZFS
        if os_key not in ("FreeBSD", "Linux"):
            continue

        # Create ZFS pools
        pools = spec.get("pools", [])
        for pool in pools:
            _add_pool_ops(state, host, pool, os_key)

        # Create ZFS datasets
        datasets = spec.get("datasets", [])
        for dataset in datasets:
            _add_dataset_ops(state, host, dataset, os_key)

        # Configure snapshots
        snapshots = spec.get("snapshots", [])
        for snapshot in snapshots:
            _add_snapshot_ops(state, host, snapshot)

        # Configure NFS exports
        nfs_config = spec.get("nfs_config", {})
        if nfs_config.get("exports"):
            _add_nfs_exports(state, host, nfs_config, os_key)

        # Configure Samba shares
        samba_config = spec.get("samba_config", {})
        if samba_config.get("shares"):
            _add_samba_shares(state, host, samba_config, os_key)


def _add_pool_ops(state, host, pool, os_key):
    """Create and configure ZFS pool."""
    pool_name = pool.get("name")
    devices = pool.get("devices", [])
    pool_type = pool.get("type", "raidz1")
    ashift = pool.get("ashift", 12)
    compression = pool.get("compression", "lz4")
    autotrim = pool.get("autotrim", True)

    if not devices:
        return

    # Build device spec based on RAID type
    if pool_type == "mirror" and len(devices) >= 2:
        device_spec = " ".join(devices)
    elif pool_type.startswith("raidz"):
        device_spec = " ".join(devices)
    else:
        device_spec = " ".join(devices)

    # Create pool
    add_op(
        state,
        server.shell,
        name=f"Create ZFS pool {pool_name} on {host.name}",
        commands=[
            f"zpool create -o ashift={ashift} -O compression={compression} "
            f"{pool_name} {pool_type} {device_spec} || true",
        ],
        host=host,
    )

    # Enable features
    if autotrim:
        add_op(
            state,
            server.shell,
            name=f"Enable autotrim on pool {pool_name} on {host.name}",
            commands=[
                f"zpool set autotrim=on {pool_name}",
            ],
            host=host,
        )

    # Enable compression on pool level
    add_op(
        state,
        server.shell,
        name=f"Set compression on pool {pool_name} on {host.name}",
        commands=[
            f"zfs set compression={compression} {pool_name}",
        ],
        host=host,
    )


def _add_dataset_ops(state, host, dataset, os_key):
    """Create and configure ZFS dataset."""
    pool = dataset.get("pool")
    name = dataset.get("name")
    mountpoint = dataset.get("mountpoint")
    quota = dataset.get("quota")
    compression = dataset.get("compression")

    dataset_path = f"{pool}/{name}" if name else pool

    # Create dataset
    cmd = f"zfs create {dataset_path}"
    if mountpoint:
        cmd += f" -o mountpoint={mountpoint}"
    if quota:
        cmd += f" -o quota={quota}"
    if compression:
        cmd += f" -o compression={compression}"
    cmd += " || true"

    add_op(
        state,
        server.shell,
        name=f"Create ZFS dataset {dataset_path} on {host.name}",
        commands=[cmd],
        host=host,
    )

    # Configure NFS if needed
    if dataset.get("nfs_share"):
        add_op(
            state,
            server.shell,
            name=f"Enable NFS for {dataset_path} on {host.name}",
            commands=[
                f"zfs set sharenfs=on {dataset_path}",
            ],
            host=host,
        )

    # Configure SMB if needed
    if dataset.get("smb_share"):
        add_op(
            state,
            server.shell,
            name=f"Enable SMB for {dataset_path} on {host.name}",
            commands=[
                f"zfs set sharesmb=on {dataset_path}",
            ],
            host=host,
        )


def _add_snapshot_ops(state, host, snapshot):
    """Configure ZFS snapshot creation."""
    dataset = snapshot.get("dataset")
    name = snapshot.get("name")
    recursive = snapshot.get("recursive", False)

    recursive_flag = "-r" if recursive else ""

    add_op(
        state,
        server.shell,
        name=f"Create snapshot {dataset}@{name} on {host.name}",
        commands=[
            f"zfs snapshot {recursive_flag} {dataset}@{name}",
        ],
        host=host,
    )


def _add_nfs_exports(state, host, nfs_config, os_key):
    """Configure NFS exports."""
    exports = nfs_config.get("exports", [])

    # Install NFS utilities if needed
    if os_key == "FreeBSD":
        add_op(
            state,
            server.shell,
            name=f"Enable NFS server on {host.name}",
            commands=[
                "echo 'nfs_server_enable=\"YES\"' >> /etc/rc.conf.local 2>/dev/null || true",
                "service nfsd start || true",
            ],
            host=host,
        )
    elif os_key == "Linux":
        add_op(
            state,
            server.shell,
            name=f"Enable NFS server on {host.name}",
            commands=[
                "systemctl enable nfs-server || true",
                "systemctl start nfs-server || true",
            ],
            host=host,
        )

    # Create /etc/exports entries
    export_lines = []
    for export in exports:
        dataset = export.get("dataset")
        clients = export.get("clients", ["*"])
        options = export.get("options", "ro")

        mountpoint = f"/mnt/{dataset.split('/')[-1]}"  # Infer from dataset name
        for client in clients:
            export_lines.append(f"{mountpoint} {client}({options})")

    if export_lines:
        add_op(
            state,
            server.shell,
            name=f"Configure NFS exports on {host.name}",
            commands=[
                f"echo '{chr(10).join(export_lines)}' >> /etc/exports",
                "exportfs -a" if os_key == "Linux" else "service nfsd reload || true",
            ],
            host=host,
        )


def _add_samba_shares(state, host, samba_config, os_key):
    """Configure Samba shares."""
    if os_key not in ("FreeBSD", "Linux"):
        return

    shares = samba_config.get("shares", [])

    # Install Samba
    add_op(
        state,
        server.shell,
        name=f"Install Samba on {host.name}",
        commands=[
            "pkg install -y samba48" if os_key == "FreeBSD" else "apt-get install -y samba",
        ],
        host=host,
    )

    # Generate smb.conf entries
    smb_config_lines = []
    for share in shares:
        name = share.get("name")
        path = share.get("path")
        comment = share.get("comment", "")
        permissions = share.get("permissions", "public")

        smb_config_lines.append(f"""[{name}]
    comment = {comment}
    path = {path}
    public = yes
    writable = no
    printable = no
""")

    if smb_config_lines:
        add_op(
            state,
            server.shell,
            name=f"Configure Samba shares on {host.name}",
            commands=[
                f"echo '{chr(10).join(smb_config_lines)}' >> /etc/samba/smb.conf",
                "smbcontrol smbd reload-config" if os_key == "FreeBSD" else "systemctl reload smbd",
            ],
            host=host,
        )
