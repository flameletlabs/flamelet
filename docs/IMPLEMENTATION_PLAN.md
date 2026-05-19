# Flamelet v2 Framework - Implementation Plan for Missing Service Tags

## Current Status: 14/22 Core Operations Implemented

### ✅ COMPLETED (Tier 1 - Production Ready)

```
Phase 1:  users, groups, sudo
Phase 2:  packages, sysctl, sysrc, timezone, services
Phase 3:  wireguard, unbound, pf
Phase 4:  monit, node_exporter
Phase 5:  opensmtpd
Phase 6:  docker
Utility:  files, get_url, lineinfile, blockinfile, copy, shell, raw, systemd
```

### ⏳ PENDING (Tier 2 - Required for Full Infrastructure)

**1. k3s** (Kubernetes)
- **Type**: Complex (server + worker bootstrap)
- **File**: `core/operations/k3s.py`
- **Features needed**:
  - Server installation (`curl get.k3s.io`)
  - Worker node joining with token
  - kubeconfig extraction
  - CNI configuration (Flannel)
  - Service CIDR + Cluster CIDR
  - TLS SANs for API server
  - Wait for cluster ready (port 6443)
- **Tenant config format**:
  ```python
  K3S = {
    "k3s.example.com": {
      "role": "server",  # or "worker"
      "cluster_cidr": "10.42.0.0/16",
      "service_cidr": "10.43.0.0/16",
      "server_url": "https://k3s-server:6443",  # for workers
      "token": "...",  # for workers
      "node_ip": "10.0.0.100",
      "advertise_address": "10.0.0.100",
      "flannel_iface": "eth0",
      "disable": ["traefik", "servicelb"],  # components to disable
      "extra_args": "--tls-san k3s.example.com"
    }
  }
  ```

**2. virtualization** (vm-bhyve + Bastille jails)
- **Type**: Complex (hypervisor setup + guest management)
- **File**: `core/operations/virtualization.py`
- **Features needed**:
  - vm-bhyve initialization
  - VM switch creation
  - Guest image management (qcow2 download)
  - VM boot/start/stop
  - Bastille jail creation
  - Jail networking
  - Jail package pre-loading
- **Tenant config format**:
  ```python
  VIRTUALIZATION = {
    "virt.example.com": {
      "hypervisor": "vm-bhyve",  # or "bastille"
      "storage": "zfs:tank/vm",
      "switches": [
        {"name": "public", "type": "manual", "bridge": "bridge0"}
      ],
      "images": [
        "https://cloud.debian.org/images/cloud/bookworm/.../debian-12.qcow2"
      ],
      "guests": [
        {
          "name": "debian-1",
          "image": "debian-12.qcow2",
          "memory": "2G",
          "cpus": 2,
          "switch": "public",
          "loader": "uefi"
        }
      ]
    }
  }
  ```

**3. storage** (ZFS + NAS configuration)
- **Type**: Complex (dataset management + backup setup)
- **File**: `core/operations/storage.py`
- **Features needed**:
  - ZFS pool creation
  - Dataset creation/management
  - ZFS snapshots + replication
  - NFS/SMB exports
  - Backup scheduling (UrBackup, BackupPC)
  - Samba SMB configuration
  - Mount point management
- **Tenant config format**:
  ```python
  STORAGE = {
    "nas.example.com": {
      "pools": [
        {"name": "tank", "disks": ["ada0", "ada1"], "raid": "mirror"}
      ],
      "datasets": [
        {
          "name": "tank/home",
          "mountpoint": "/tank/home",
          "compression": "lz4",
          "dedup": "off"
        }
      ],
      "exports": {
        "nfs": ["/tank/home", "/tank/shared"],
        "smb": [{"path": "/tank/shared", "share": "shared", "guest": "ok"}]
      ],
      "backups": {
        "type": "urbackup",
        "server": "backup.example.com",
        "schedule": "daily"
      }
    }
  }
  ```

### ⏳ OPTIONAL (Tier 3 - Nice-to-Have)

**4. registry** (Docker Registry)
- Config-driven stack in docker.py (compose)
- Minimal separate operation needed

**5. nginx** (Web server + Reverse proxy)
- Standard config generation
- Similar to unbound/monit pattern
- ~150 lines

**6. postgresql** (Database server in jails)
- Jail bootstrap + package install
- Replication setup
- Could be part of storage.py

**7. grafana** (Metrics dashboard)
- Package + systemd enablement
- Config file generation
- ~100 lines

**8. prometheus** (Metrics collection)
- config.yml generation
- Scrape targets from inventory
- Alert rules
- ~150 lines

---

## Implementation Priority & Order

### Must Do (Before production)
1. **k3s** — 4 of 25 hosts need it (k3s.home + 3 workers in baar)
2. **virtualization** — 4 hypervisor hosts (virt*, virt-*.baar)
3. **storage** — 1 NAS host (nas-01.pangea)

### Should Do (Within month)
4. **nginx** — Common reverse proxy (2 locations use it)
5. **postgresql** — Database infrastructure (4 jails)

### Nice-to-Have (As needed)
6. **registry** — Already in docker.py compose stacks
7. **grafana** — Monitoring dashboard
8. **prometheus** — Metrics if not using cloud provider

---

## Code Patterns from Existing Operations

All operations follow this structure:

```python
def add_<service>_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure <Service>.
    
    Args:
        state: pyinfra State object
        hosts: Inventory
        config: dict mapping hostname → service config
            {
                "example.host": {
                    "key": "value",
                    ...
                }
            }
        target_hosts: list of Host objects (optional)
        task: "service" or "all" (for dispatch)
    """
    targets = target_hosts if target_hosts else list(hosts)
    
    for host in targets:
        if host.name not in config:
            continue
            
        os_key = host.get_fact(Kernel)
        service_config = config[host.name]
        
        # Handle per-OS paths
        if os_key == "FreeBSD":
            conf_path = "/usr/local/etc/<service>/<name>.conf"
        elif os_key == "OpenBSD":
            conf_path = "/etc/<service>/<name>.conf"
        else:  # Linux
            conf_path = "/etc/<service>/<name>.conf"
        
        # Generate config content
        content = _generate_<service>_config(service_config)
        
        # Write config file
        add_op(state, files.put, ...)
        
        # Enable service
        if os_key == "FreeBSD":
            add_op(state, server.shell, 
                commands=[f"sysrc <service>_enable=YES", ...])
        elif os_key == "Linux":
            add_op(state, server.shell,
                commands=["systemctl enable <service>", ...])
        
        # Validate + reload
        add_op(state, server.shell,
            commands=[f"<service> validate", f"<service> reload"])

def _generate_<service>_config(config):
    """Generate service config from tenant vars."""
    lines = []
    lines.append("# Generated by flamelet v2")
    # ... build config ...
    return "\n".join(lines)
```

---

## Next Steps

1. **Immediate**: Implement k3s operation (~300 lines)
   - Test on k3s.home + k3s-*.baar hosts
   - Validate kubeconfig extraction

2. **Week 1**: Implement virtualization operation (~400 lines)
   - Test vm-bhyve on virt.home
   - Test Bastille jails on virt-*.baar

3. **Week 2**: Implement storage operation (~300 lines)
   - Test ZFS on nas-01.pangea
   - Test NFS/SMB exports

4. **Ongoing**: Populate remaining host configs (vars/hosts/*.py)
   - 22 stub configs need service-specific settings
   - Use existing patterns from virt_home.py

