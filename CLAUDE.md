# Flamelet Framework Documentation

## Overview

Flamelet is a multi-tenant infrastructure automation framework built on pyinfra. It separates concerns:
- **Framework** (`~/src/floads/flamelet/core/`): Operations, tasks, config loaders, CLI
- **Tenants** (`~/.config/flamelet/tenants/`): Variables, inventory, host definitions

A tenant only needs:
- `inventory.py` — host definitions and groups
- `vars/__init__.py` — users and constants
- `vars/all.py`, `vars/location/*.py`, `vars/hosts/*.py` — configuration by tier

The framework provides:
- `flamelet` CLI — replaces tenant `run.py`
- TASK_REGISTRY — maps task names to operations
- Config loaders — 3-tier inheritance (all < location < host-specific)
- 21 operations — each operation function follows a standard signature

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

Returns dict like: `{"virt.home": {...}, "core": {...}}`

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

### Example: vars/hosts/virt_home.py

```python
MONIT = {
    "virt.home": {
        "daemon": 120,
        "checks": {
            "system": "check system virt.home\n  if memory usage > 75% then alert",
            ...
        }
    }
}

WIREGUARD = {
    "virt.home": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.2/24",
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

For host `virt.home` in location `home`:

1. `vars/all.py` → `MONIT` (if exists)
2. `vars/location/home.py` → `MONIT["virt.home"]` (if exists)
3. `vars/hosts/virt_home.py` → `MONIT["virt.home"]` (if exists)

Final config = merge of all three in order (host-specific wins).

---

## CLI Examples

```bash
# Deploy all tasks to all hosts
flamelet

# Dry-run
flamelet --dry

# Single host
flamelet --limit virt.home

# Single task
flamelet --task monit --limit virt.home

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

## Best Practices

1. **Separate concerns**: Framework = operations, Tenant = configuration
2. **3-tier inheritance**: Use all.py for defaults, location for environment, hosts for specifics
3. **Config validation**: Load and inspect config before adding operations
4. **Hostname as anchor**: All service configs are hostname-keyed; packages are OS-keyed
5. **No Python logic in vars**: Vars files are pure data; logic lives in operations
6. **Error handling**: Operations should skip missing config gracefully (not fail)
7. **Documenting operations**: Each operation function should state its config_attr requirements in the docstring

