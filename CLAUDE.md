# Flamelet Framework — Complete Reference for AI

**This document is designed for AI systems to generate complete, production-ready tenant configurations.**

## Core Principle

```
Framework (Reusable)          Tenant (Configuration Only)
├── core/operations/ ────────→ vars/all.py
├── core/tasks/      ────────→ vars/location/*.py
├── core/cli.py      ────────→ vars/hosts/*.py
└── TASK_REGISTRY    ────────→ inventory.py
```

**Rule:** Add all NEW tasks/operations to the framework. Tenants hold ONLY configuration data (no logic).

---

## Tenant Contract (What AI Needs to Generate)

A complete tenant requires exactly these files:

```
tenant-name/
├── inventory.py              # REQUIRED: host definitions + groups
└── vars/
    ├── __init__.py           # REQUIRED: users, groups, constants
    ├── all.py                # OPTIONAL: global defaults (services, packages)
    ├── location/
    │   └── {location}.py     # OPTIONAL: location-specific overrides
    └── hosts/
        └── {hostname}.py     # OPTIONAL: host-specific configs
```

**That's it.** No `run.py`. No logic. Just configuration.

---

## Architecture

### TASK_REGISTRY

Located in `core/tasks/__init__.py`. Maps task names to operations:

```python
TASK_REGISTRY = {
    "users": [TaskEntry(add_user_ops, None, "users")],
    "wireguard": [TaskEntry(add_wireguard_ops, "WIREGUARD", "standard")],
    "autossh": [
        TaskEntry(add_autossh_ops, "AUTOSSH_TUNNELS", "autossh"),
        TaskEntry(add_autossh_gateway_ops, "AUTOSSH_GATEWAY", "autossh"),
    ],
    ...
}
```

Each `TaskEntry` has:
- `op_func`: The operation function to call
- `config_attr`: Attribute name in tenant vars (e.g., "WIREGUARD", "MONIT") — `None` for users/sudo
- `op_type`: How config is loaded ("standard", "autossh", "packages", "users", "sudo")

### Config Loaders

Located in `core/tasks/loader.py`:

#### `load_service_config(tenant_path, attr_name) → dict`
Load hostname-keyed service config via 3-tier inheritance:
1. `vars/all.py` — framework defaults
2. `vars/location/{location}.py` — location overrides (extracted from hostname)
3. `vars/hosts/{host}.py` — host-specific overrides

Returns dict like: `{"virt.example.com": {...}, "core": {...}}`

#### `load_packages_config(tenant_path, host_name, os_key) → dict`
Load OS-keyed package list for a specific host:
1. `vars/all.py` PACKAGES[os_key]
2. `vars/location/{location}.py` PACKAGES[os_key]
3. `vars/hosts/{host}.py` PACKAGES[os_key]

Returns dict like: `{"FreeBSD": ["package1", "package2"]}`

---

## Operation Signature

All operations follow this pattern:

```python
def add_<service>_ops(state, hosts, config, target_hosts=None, task="all"):
    """
    Args:
        state: pyinfra State object (use with add_op())
        hosts: pyinfra Inventory object
        config: service-specific config dict (hostname-keyed or OS-keyed)
        target_hosts: optional list of Host objects to limit to
        task: task name being run (for conditional execution)
    """
```

### Special Cases

**Users operation:**
```python
def add_user_ops(state, hosts, users_config, group_names, target_hosts=None, task="all"):
```
- `users_config`: dict of {username: {...}}
- `group_names`: list of group names to create

**Packages operation:**
```python
def add_package_ops(state, hosts, config, target_hosts=None, task="all"):
```
- `config`: dict like {os_key: [pkg_list]} — OS-keyed, not hostname-keyed

**AutoSSH operations:**
Two separate operations for tunnels and gateway:
- `add_autossh_ops(state, hosts, config_tunnels, target_hosts, task)`
- `add_autossh_gateway_ops(state, hosts, config_gateway, target_hosts, task)`

Both called when `task == "autossh"`.

---

## How the CLI Works

### 1. Discovery
```bash
flamelet [OPTIONS]
```

- Finds framework via `FRAMEWORK_ROOT` env var, `~/.local/share/flamelet`, or upward search
- Finds tenant via `TENANT_PATH` env var, `~/.config/flamelet/tenants`, or CWD
- Loads `inventory.py` and `vars/__init__.py` from tenant

### 2. Task Resolution
- `--task all` → runs all registry keys
- `--task monit` → runs `TASK_REGISTRY["monit"]` entries
- `--task users` → runs user provisioning (special case)

### 3. Config Loading
For each task:
- If `config_attr` exists: calls `load_service_config(tenant_path, config_attr)`
- If `op_type == "packages"`: calls `load_packages_config()` per-host
- If `op_type == "users"`: loads from `tenant_vars.USERS` and `tenant_vars.GROUPS`

### 4. Operation Dispatch
For each `TaskEntry` in the task's list:
- Calls `op_func(state, inventory, config, target_hosts, task)`
- Config is pre-loaded (or empty if not in vars)

---

## Adding a New Operation

1. Create `core/operations/myservice.py`:
   ```python
   def add_myservice_ops(state, hosts, config, target_hosts=None, task="all"):
       # Use add_op() to queue operations
       # config is hostname-keyed: {"hostname": {...}}
   ```

2. Register in `core/tasks/__init__.py`:
   ```python
   # Add to _init_registry() before return:
   "myservice": [TaskEntry(add_myservice_ops, "MYSERVICE", "standard")],
   ```

3. Add config to tenant:
   ```python
   # vars/hosts/example.py
   MYSERVICE = {
       "hostname": {
           "setting1": "value",
           ...
       }
   }
   ```

4. Deploy:
   ```bash
   flamelet --task myservice
   ```

---

## Operation Implementation Pattern

Use pyinfra's `add_op()` API (not the `@operation` decorator):

```python
from pyinfra.api import add_op
from pyinfra.operations import files

def add_myservice_ops(state, hosts, config, target_hosts=None, task="all"):
    targets = target_hosts if target_hosts else list(hosts)
    
    for host in targets:
        if host.name not in config:
            continue
        
        host_config = config[host.name]
        
        # Queue a file write
        add_op(
            state,
            files.put,
            name=f"Configure myservice on {host.name}",
            src="content here",
            dest="/etc/myservice/config",
            mode="0644",
            user="root",
            group="root",
            host=host,  # Important: pin op to specific host
        )
```

Key points:
- Always use `host=host` parameter to pin to specific host
- Skip hosts not in config dict
- Use the `name=` parameter to describe the operation
- Import operations from pyinfra submodules (e.g., `pyinfra.operations.files`)

---

## Tenant Structure (Contract)

### Required Files

```
inventory.py                    # Must define build_inventory()
vars/__init__.py               # Must define USERS, GROUPS, BASH, SUDO_GROUP
vars/all.py                    # Global defaults (all services)
```

### Optional Files

```
vars/location/{location}.py    # Location-specific overrides (extracted from hostname)
vars/hosts/{hostname}.py       # Host-specific overrides
```

### Example: vars/hosts/virt_prod.py

```python
MONIT = {
    "virt.example.com": {
        "daemon": 120,
        "checks": {
            "system": "check system virt.example.com\n  if memory usage > 75% then alert",
            ...
        }
    }
}

WIREGUARD = {
    "virt.example.com": {
        "interfaces": {
            "wg0": {
                "address": "10.100.0.2/24",
                ...
            }
        }
    }
}
```

### Example: vars/__init__.py

```python
USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": "$6$...",
        "groups": {"FreeBSD": "wheel", "OpenBSD": "wheel", "Linux": "sudo"},
        "shell": {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"},
        "public_keys": [...],
    }
}

GROUPS = ["syseng", "keep"]
BASH = {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"}
SUDO_GROUP = {"FreeBSD": "wheel", "Linux": "sudo"}
LUMACA_PASSWORD = "$6$..."
```

---

## Configuration Inheritance Example

For host `virt.example.com` in location name (e.g., "prod")`:

1. `vars/all.py` → `MONIT` (if exists)
2. `vars/location name (e.g., "prod").py` → `MONIT["virt.example.com"]` (if exists)
3. `vars/hosts/virt_prod.py` → `MONIT["virt.example.com"]` (if exists)

Final config = merge of all three in order (host-specific wins).

---

## CLI Examples

```bash
# Deploy all tasks to all hosts
flamelet

# Dry-run
flamelet --dry

# Single host
flamelet --limit virt.example.com

# Single task
flamelet --task monit --limit virt.example.com

# Verbose
flamelet -v --task users

# All tasks, single host, dry-run
flamelet --dry --limit core --task all
```

---

## Debugging

### Check TASK_REGISTRY

```python
from core.tasks import TASK_REGISTRY
print(TASK_REGISTRY.keys())  # All available tasks
```

### Validate Config Loading

```python
from pathlib import Path
from core.tasks.loader import load_service_config

tenant_path = Path("~/.config/flamelet/tenants/flamelet-home")
config = load_service_config(tenant_path, "MONIT")
print(config.keys())  # All hosts with MONIT config
```

### Test CLI Discovery

```bash
TENANT_PATH=~/.config/flamelet/tenants/flamelet-home \
FRAMEWORK_ROOT=~/src/floads/flamelet \
flamelet --help
```

---

## Complete Operation Reference (For Generating Tenant Configs)

This section lists all 20 operations with their config attributes so AI can generate correct tenant variables.

### Users & System

#### `users` — User & Group Provisioning
**Config Attribute:** None (loaded from `vars/__init__.py` directly)

```python
# vars/__init__.py
USERS = {
    "username": {
        "comment": "Full Name",
        "password": "$6$...",  # sha-512 hash from mkpasswd --method=sha-512
        "groups": {"FreeBSD": "wheel", "Linux": "sudo"},  # OS-specific groups
        "shell": {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"},  # OS-specific
        "public_keys": ["ssh-rsa AAAA...", "ssh-ed25519 AAAA..."],
    }
}

GROUPS = ["wheel", "keep"]  # System groups to create
BASH = {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"}  # Default shell per OS
SUDO_GROUP = {"FreeBSD": "wheel", "Linux": "sudo"}  # Sudo group per OS
LUMACA_PASSWORD = "$6$..."  # Default password hash for all users
```

#### `sudo` — Sudoers Configuration
**Config Attribute:** None (loaded from `vars/__init__.py` directly)

Uses USERS config from above.

### Package Management

#### `packages` — Package Installation
**Config Attribute:** `PACKAGES` (OS-keyed, not hostname-keyed)

```python
# vars/all.py
PACKAGES = {
    "Linux": ["curl", "git", "htop", "openssh-server"],
    "FreeBSD": ["curl", "git", "htop"],
    "OpenBSD": ["curl", "git", "htop"],
}
```

#### `package-update` — Upgrade All Installed Packages
**Config Attribute:** None — no tenant configuration required

Refreshes package indexes and upgrades all installed packages to latest versions.

```bash
flamelet --task package-update                  # upgrade all hosts
flamelet --task package-update --limit web      # upgrade one group
flamelet --task package-update --dry            # show what would run
flamelet --task package-update --dry --diff     # show exact commands
```

OS dispatch: apt (Debian/Ubuntu) · apk (Alpine) · pkg (FreeBSD) · pkg_add -u (OpenBSD)

### Networking

#### `wireguard` — WireGuard VPN
**Config Attribute:** `WIREGUARD` (hostname-keyed)

```python
# vars/all.py or vars/hosts/vpn_home.py
WIREGUARD = {
    "vpn.example.com": {
        "interfaces": {
            "wg0": {
                "address": "10.0.0.1/24",
                "port": 51820,
                "private_key": "...",
                "peers": [
                    {
                        "pubkey": "...",
                        "allowed_ips": ["10.0.0.0/24"],
                        "endpoint": "peer.example.com:51820",  # format: "host:port"
                        "keepalive": 25,
                        "preshared_key": "...",  # Optional
                    }
                ]
            }
        }
    }
}
```

**Endpoint Format:** Specify as `"host:port"` in the Python config. The framework automatically formats it correctly for each OS:
- **OpenBSD**: Generated as `wgendpoint host port` (space-separated in /etc/hostname.wg0)
- **FreeBSD/Linux**: Generated as `Endpoint = host:port` (colon-separated)

#### `unbound` — DNS Resolver
**Config Attribute:** `UNBOUND` (hostname-keyed)

```python
UNBOUND = {
    "dns.example.com": {
        "listen_on": ["127.0.0.1", "10.0.0.1"],
        "access_control": [
            "127.0.0.0/8 allow",
            "10.0.0.0/24 allow",
            "0.0.0.0/0 refuse",
        ],
        "local_data": [
            {"name": "host.local.", "type": "A", "value": "10.0.0.10"},
            {"name": "alias.local.", "type": "CNAME", "value": "host.local."},
        ],
        "forward_zones": [
            {"name": ".", "addrs": ["1.1.1.1", "8.8.8.8"]},
        ],
    }
}
```

#### `autossh` — SSH Reverse Tunnels
**Config Attributes:** `AUTOSSH_TUNNELS` and `AUTOSSH_GATEWAY` (both hostname-keyed)

```python
# vars/hosts/app_home.py — tunnel from remote to gateway
AUTOSSH_TUNNELS = {
    "app.example.com": {
        "remote_host": "gateway.example.com",
        "remote_user": "autossh",
        "local_port": 2220,
        "local_target": "localhost:22",
        "private_key": "/root/.ssh/id_rsa-autossh",
    }
}

# vars/hosts/gateway.py — gateway receives tunnel
AUTOSSH_GATEWAY = {
    "gateway.example.com": {
        "authorized_keys": {
            "user": "autossh",
            "keys": [
                {
                    "comment": "app.example.com",
                    "public_key": "ssh-rsa AAAA...",
                    "options": "no-pty,no-agent-forwarding",
                }
            ]
        }
    }
}
```

### System Configuration

#### `sysctl` — Kernel Parameters
**Config Attribute:** `SYSCTL` (hostname-keyed)

```python
SYSCTL = {
    "app.prod": {
        "net.ipv4.ip_forward": "1",
        "net.ipv4.conf.all.send_redirects": "0",
        "vm.swappiness": "10",
    }
}
```

#### `services` — Service Management
**Config Attribute:** `SERVICES` (hostname-keyed)

```python
SERVICES = {
    "app.example.com": {
        "enabled": ["ssh", "ntp"],
        "started": ["ssh", "ntp"],
        "restart": ["app-service"],  # Services to restart
    }
}
```

#### `pf` — BSD Firewall Rules
**Config Attribute:** `PF` (hostname-keyed)

```python
PF = {
    "gateway.example.com": {
        "rules": """
block in all
pass in on em0 proto tcp from any to any port 22
pass in on wg0 proto tcp from any to any port 443
""",
    }
}
```

### Monitoring & Observability

#### `monit` — Process & System Monitoring
**Config Attribute:** `MONIT` (hostname-keyed)

```python
MONIT = {
    "app.example.com": {
        "daemon": 120,  # Check interval in seconds
        "mmonit_url": "https://monit:password@monit.example.com/collector",
        "mmonit_hostgroup": "home",
        "httpd_port": 2812,
        "httpd_password": "monitoring-ui-password",
        "checks": {
            "system": "check system app.example.com\n  if memory usage > 75% then alert",
            "filesystem_root": "check filesystem rootfs with path /\n  if space usage > 90% then alert",
            "process_sshd": "check process sshd with pidfile /var/run/sshd.pid\n  if failed port 22 then restart",
        }
    }
}
```

#### `node_exporter` — Prometheus Exporter
**Config Attribute:** `NODE_EXPORTER` (hostname-keyed)

```python
NODE_EXPORTER = {
    "app.example.com": {
        "port": 9100,
        "collectors": ["filesystem", "meminfo", "netdev"],
        "options": "--collector.disable-defaults",
    }
}
```

#### `prometheus` — Metrics Server
**Config Attribute:** `PROMETHEUS` (hostname-keyed)

```python
PROMETHEUS = {
    "metrics.example.com": {
        "port": 9090,
        "scrape_interval": "15s",
        "targets": [
            {"job": "node", "targets": ["localhost:9100", "app.example.com:9100"]},
            {"job": "blackbox", "targets": ["localhost:9115"]},
        ],
    }
}
```

### Mail & DNS

#### `opensmtpd` — Mail Relay
**Config Attribute:** `OPENSMTPD` (hostname-keyed)

```python
OPENSMTPD = {
    "mail.example.com": {
        "listen": ["127.0.0.1:25", "10.0.0.1:25"],
        "relay": "smtp.example.com:587",
        "relay_auth": {"user": "alerts@example.com", "password": "..."},
    }
}
```

### Container & Virtualization

#### `docker` — Docker Installation & Config
**Config Attribute:** `DOCKER` (hostname-keyed)

```python
DOCKER = {
    "docker.example.com": {
        "registry": "registry.example.com",
        "registry_auth": {"username": "user", "password": "..."},
        "storage_driver": "overlay2",
        "log_driver": "json-file",
        "log_opts": {"max-size": "10m", "max-file": "3"},
    }
}
```

#### `registry` — Container Registry
**Config Attribute:** `REGISTRY` (hostname-keyed)

```python
REGISTRY = {
    "registry.example.com": {
        "port": 5000,
        "storage": "/var/lib/registry",
        "auth": {"htpasswd_file": "/etc/registry/htpasswd"},
    }
}
```

#### `virtualization` — bhyve VM Management
**Config Attribute:** `VIRTUALIZATION` (hostname-keyed)

```python
VIRTUALIZATION = {
    "virt.example.com": {
        "type": "bhyve",
        "zvol_pool": "vm-pool",
        "bridges": [
            {"name": "vm-bridge0", "interface": "em0"},
        ],
        "vms": [
            {
                "name": "app-01",
                "vcpu": 4,
                "memory": "4G",
                "disk_size": "20G",
                "network": "vm-bridge0",
                "autostart": True,
            }
        ]
    }
}
```

#### `bastille` — FreeBSD Bastille Jail Management
**Config Attribute:** `BASTILLE` (hostname-keyed, FreeBSD-only)

Creates and configures VNET thick jails using Bastille. Handles release
bootstrapping, jail creation, networking, SSH access, and package installation.

```python
BASTILLE = {
    "virt.example.com": {
        "release": "14.3-RELEASE",   # FreeBSD release to bootstrap
        "bridge": "bridge10",         # VNET bridge interface
        "zfs_enable": True,           # Use ZFS for jail storage
        "zfs_zpool": "zroot",         # ZFS pool name
        "jails": [
            {
                "name": "db",
                "release": "14.3-RELEASE",
                "ip": "10.0.0.51/24",    # static IP; use "0.0.0.0" for DHCP
                "gateway": "10.0.0.1",
                "thick": True,            # thick jail (full OS copy)
                "static_mac": True,       # stable MAC across restarts
                "sysvipc": True,          # needed for PostgreSQL/MariaDB
                "allow": {"raw_sockets": 1},  # allow.* jail flags
                "packages": ["mariadb1011-server", "python3"],
                "ssh": True,              # enable sshd + copy authorized_keys
                "authorized_keys_src": "/root/.ssh/authorized_keys",
                "autostart": True,
            },
        ],
    }
}
```

#### `k3s` — Kubernetes (k3s)
**Config Attribute:** `K3S` (hostname-keyed)

```python
K3S = {
    "k3s.example.com": {
        "role": "server",  # or "agent"
        "cluster_token": "...",
        "server": "https://k3s.example.com:6443",
        "datastore": "sqlite3",  # or "etcd"
    }
}
```

### Storage

#### `storage` — ZFS/NFS/SMB
**Config Attribute:** `STORAGE` (hostname-keyed)

```python
STORAGE = {
    "nas.example.com": {
        "pools": [
            {
                "name": "tank",
                "devices": ["/dev/da0", "/dev/da1"],
                "type": "mirror",
                "compression": "lz4",
            }
        ],
        "datasets": [
            {
                "pool": "tank",
                "name": "data",
                "mountpoint": "/mnt/data",
                "quota": "5T",
                "nfs_share": True,
                "smb_share": True,
            }
        ],
        "nfs_config": {
            "exports": [
                {
                    "dataset": "tank/data",
                    "clients": ["10.0.0.0/24"],
                    "options": "rw,no_root_squash",
                }
            ]
        },
        "samba_config": {
            "shares": [
                {
                    "name": "media",
                    "path": "/mnt/media",
                    "comment": "Shared Media",
                    "permissions": "public",
                }
            ]
        },
    }
}
```

### Web Services

#### `nginx` — Reverse Proxy
**Config Attribute:** `NGINX` (hostname-keyed)

```python
NGINX = {
    "nginx.example.com": {
        "user": "www-data",
        "worker_processes": 4,
        "upstream": [
            {
                "name": "api",
                "servers": ["127.0.0.1:8080", "127.0.0.1:8081"],
            }
        ],
        "servers": [
            {
                "listen": "80",
                "server_name": "example.com",
                "locations": [
                    {
                        "path": "/api",
                        "proxy_pass": "http://api",
                    }
                ],
            }
        ],
    }
}
```

#### `postgresql` — PostgreSQL Database
**Config Attribute:** `POSTGRESQL` (hostname-keyed)

```python
POSTGRESQL = {
    "db.example.com": {
        "version": "15",
        "listen_addresses": ["127.0.0.1", "10.0.0.5"],
        "port": 5432,
        "max_connections": 100,
        "shared_buffers": "256MB",
        "databases": [
            {
                "name": "appdb",
                "owner": "appuser",
                "encoding": "UTF8",
            }
        ],
        "users": [
            {
                "name": "appuser",
                "password": "...",
                "privileges": "ALL ON DATABASE appdb",
            }
        ],
    }
}
```

---

## 3-Tier Configuration Inheritance

For hostname `app-prod.example.com`:

1. **Global Defaults** (`vars/all.py`) — required minimum config
2. **Location Override** (`vars/location name (e.g., "prod").py`) — environment-specific changes
   - Location extracted from last dot segment: `app-prod.example.com` → `home`
3. **Host Override** (`vars/hosts/app_prod_home.py`) — host-specific changes
   - Filename format: `<hostname>` with `.` and `-` replaced by `_`

Final config = merge of all three, with host-specific winning.

---

## How AI Should Generate Tenant Configs

### Step 1: Read This Document
Understand all 20 operations and their config attributes.

### Step 2: Create inventory.py
```python
from pyinfra.api.inventory import Inventory

def build_inventory():
    return Inventory(
        (
            [
                ("app.example.com", {"ssh_hostname": "10.0.0.10"}),
                ("db.example.com", {"ssh_hostname": "10.0.0.20"}),
            ],
            {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"},
        ),
        web=(["app.example.com"], {}),
        db=(["db.example.com"], {}),
    )
```

### Step 3: Create vars/__init__.py
```python
USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": "$6$...",
        "groups": {"FreeBSD": "wheel", "Linux": "sudo"},
        "shell": {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"},
        "public_keys": ["ssh-rsa AAAA..."],
    }
}

GROUPS = ["wheel", "keep"]
BASH = {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"}
SUDO_GROUP = {"FreeBSD": "wheel", "Linux": "sudo"}
LUMACA_PASSWORD = "$6$..."
```

### Step 4: Create vars/all.py
```python
PACKAGES = {
    "Linux": ["curl", "git", "htop"],
    "FreeBSD": ["curl", "git", "htop"],
}

# Add service configs for all hosts (global defaults)
WIREGUARD = {}  # If hosts use WireGuard
MONIT = {}      # If hosts use Monit
# ... other services
```

### Step 5: Create vars/location/{location}.py (Optional)
For location-specific overrides (e.g., prod vs. dev environments).

### Step 6: Create vars/hosts/{hostname}.py (Optional)
For host-specific configs (specific VMs, databases, services).

**That's it.** No run.py. No logic. Just configuration.

---

## Adding New Operations to Framework (NOT Tenant)

**IMPORTANT:** Always add NEW operations to the framework, never to tenant code.

### Step 1: Create Operation Module

Create `core/operations/myservice.py`:

```python
from pyinfra.api import add_op
from pyinfra.operations import files, server

def add_myservice_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy MyService.
    
    Config attribute: MYSERVICE (hostname-keyed dict)
    
    Args:
        state: pyinfra State
        hosts: pyinfra Inventory
        config: dict like {"hostname": {"setting1": "value"}}
        target_hosts: optional list of Host objects to limit to
        task: task name being run
    """
    targets = target_hosts if target_hosts else list(hosts)
    
    for host in targets:
        if host.name not in config:
            continue
        
        host_config = config[host.name]
        
        # Write config file
        add_op(
            state,
            files.put,
            name=f"Deploy MyService config to {host.name}",
            src=generate_config(host_config),
            dest="/etc/myservice/config",
            mode="0644",
            user="root",
            group="root",
            host=host,
        )
        
        # Restart service
        add_op(
            state,
            server.shell,
            name=f"Restart MyService on {host.name}",
            commands=["systemctl restart myservice"],
            host=host,
        )

def generate_config(config):
    """Generate config file content from dict."""
    lines = [f"{k}: {v}" for k, v in config.items()]
    return "\n".join(lines)
```

### Step 2: Register in TASK_REGISTRY

Edit `core/tasks/__init__.py`:

```python
def _init_registry() -> dict[str, list[TaskEntry]]:
    """Build TASK_REGISTRY after all imports are available."""
    from core.operations.myservice import add_myservice_ops
    
    return {
        ...existing tasks...
        "myservice": [TaskEntry(add_myservice_ops, "MYSERVICE", "standard")],
    }
```

### Step 3: Document in CLAUDE.md

Add to "Complete Operation Reference" section:

```markdown
#### `myservice` — MyService Configuration
**Config Attribute:** `MYSERVICE` (hostname-keyed)

\`\`\`python
MYSERVICE = {
    "app.example.com": {
        "setting1": "value1",
        "setting2": "value2",
    }
}
\`\`\`
```

### Step 4: Add Tests

Create `tests/unit/test_myservice.py`:

```python
def test_myservice_registered(self):
    """myservice task should be registered."""
    assert "myservice" in TASK_REGISTRY
    assert TASK_REGISTRY["myservice"][0].config_attr == "MYSERVICE"
```

### Step 5: Update Tenant

In tenant `vars/hosts/app_home.py`:

```python
MYSERVICE = {
    "app.example.com": {
        "setting1": "value1",
        "setting2": "value2",
    }
}
```

Then deploy:

```bash
flamelet --task myservice --limit app.example.com --dry
flamelet --task myservice --limit app.example.com
```

---

## Best Practices

1. **Separate concerns**: Framework = operations, Tenant = configuration
2. **3-tier inheritance**: Use all.py for defaults, location for environment, hosts for specifics
3. **Config validation**: Load and inspect config before adding operations
4. **Hostname as anchor**: All service configs are hostname-keyed; packages are OS-keyed
5. **No Python logic in vars**: Vars files are pure data; logic lives in operations
6. **Error handling**: Operations should skip missing config gracefully (not fail)
7. **Documenting operations**: Each operation function should state its config_attr requirements in the docstring
8. **Always extend framework**: New tasks/operations go in core/operations/, never in tenant code
9. **Document new operations**: Always add config examples to this CLAUDE.md file

