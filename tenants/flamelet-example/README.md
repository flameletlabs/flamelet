# Example Tenant — Reference Configuration

This directory contains a complete, production-ready example tenant for the flamelet v2 framework.
It demonstrates the proper structure and configuration patterns that all tenants should follow.

---

## Structure

```
tenants/flamelet-example/
├── README.md                    ← You are here
├── inventory.py                 ← Required: host definitions and groups
└── vars/
    ├── __init__.py              ← Required: users, groups, shell configs
    ├── all.py                   ← Optional: global service defaults
    ├── location/
    │   └── example.py           ← Optional: location-specific overrides
    └── hosts/
        └── docker_example_com.py ← Optional: host-specific overrides
```

---

## Files Explained

### `inventory.py` (Required)

Defines all hosts, groups, and SSH configuration using pyinfra's Inventory API:

```python
from pyinfra.api import Inventory

def build_inventory(local=False):
    """Build example home infrastructure inventory.
    
    Args:
        local: If True, use @local connector (for CI/testing without SSH).
    """
    if local:
        # CI/testing mode: @local connector (no SSH, runs on local machine)
        return Inventory((([("@local", {})], {}),))
    
    # SSH-based inventory for real deployment
    all_hosts = [
        ("gw.example.com", {"_doas": True}),  # OpenBSD with doas
        ("nas.example.com", {"ssh_hostname": "10.0.0.10"}),  # FreeBSD
        # ... more hosts ...
    ]
    
    return Inventory(
        (all_hosts, {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"}),
        openbsd=(["gw.example.com"], {"_doas": True}),
        freebsd=([...], {"_sudo": True}),
        # ... groups ...
    )
```

**Key concepts:**
- `@local` connector for CI testing (no SSH needed)
- SSH-based for real deployment with examples.com hostnames
- Groups for privilege escalation (`_doas`, `_sudo`)
- Functional groups for targeting (e.g., "gateway", "workers")

### `vars/__init__.py` (Required)

Defines users, groups, and system constants:

```python
USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": "$6$...",  # sha-512 hash
        "groups": SUDO_GROUP,  # OS-aware (dict per OS)
        "shell": BASH,         # OS-aware (dict per OS)
        "public_keys": ["ssh-rsa AAAA..."],
    }
}

GROUPS = ["syseng", "keep"]
BASH = {"FreeBSD": "/usr/local/bin/bash", "Linux": "/bin/bash"}
SUDO_GROUP = {"FreeBSD": "wheel", "Linux": "sudo"}
```

**Key concepts:**
- `USERS` and `GROUPS` are always required
- `BASH` and `SUDO_GROUP` should be OS-aware dicts
- All data is self-contained (no imports from framework core)

### `vars/all.py` (Optional — Global Defaults)

Provides service configuration defaults for all hosts:

```python
PACKAGES = {
    "FreeBSD": ["curl", "git", "htop"],
    "Linux": ["curl", "git", "htop"],
}

MONIT = {}  # Empty by default, overridden by location/hosts
WIREGUARD = {}
DOCKER = {}
```

**Key concepts:**
- `PACKAGES` is OS-keyed (differs by OS, not by host)
- Service configs are hostname-keyed and empty by default
- Location and host files override these defaults

### `vars/location/{location}.py` (Optional — Location Overrides)

Provides location-specific configuration. Location is extracted from hostname's last dot segment:
- `gw.example.com` → location `example`
- `app.prod.example.com` → location `example.com`

```python
# vars/location/example.py
MONIT = {
    "gw.example.com": {
        "daemon": 120,
        "checks": {...}
    }
}

WIREGUARD = {
    "gw.example.com": {
        "interfaces": {"wg0": {...}}
    }
}
```

**Key concepts:**
- Merges with `all.py` (all.py first, location overrides)
- Used for environment-specific configs (prod vs. dev vs. home)

### `vars/hosts/{hostname}.py` (Optional — Host-Specific Overrides)

Provides host-specific configuration. Hostname has `.` and `-` replaced by `_`:
- `gw.example.com` → `vars/hosts/gw_example_com.py`
- `worker-1.example.com` → `vars/hosts/worker_1_example_com.py`

```python
# vars/hosts/docker_example_com.py
DOCKER = {
    "docker.example.com": {
        "storage_driver": "overlay2"
    }
}

PACKAGES = {
    "Linux": ["docker-ce", "docker-compose-plugin"]
}
```

**Key concepts:**
- Merges with `all.py` and `location/` (all.py < location < hosts)
- Most specific overrides win
- Hostname-keyed for services, OS-keyed for packages

---

## 3-Tier Configuration Inheritance

All service configurations use 3-tier inheritance:

```
all.py  (global defaults)
  ↓
location/{location}.py  (environment overrides)
  ↓
hosts/{hostname}.py  (host-specific overrides)
  ↓
Final Config
```

**Example: MONIT config for `gw.example.com`**

1. **all.py**: `MONIT = {}`  (empty global default)
2. **location/example.py**: `MONIT = {"gw.example.com": {...}}`  (location override)
3. **hosts/gw_example_com.py**: (not present, no host-specific override)
4. **Result**: Uses the location override

---

## Creating Your Own Tenant

To create a new tenant, copy this directory and customize:

```bash
cp -r tenants/flamelet-example ~/.config/flamelet/tenants/my-project
cd ~/.config/flamelet/tenants/my-project

# Edit files
vim inventory.py
vim vars/__init__.py
vim vars/all.py
# Add location/ and hosts/ as needed
```

Then deploy:

```bash
flamelet --dry --task all      # Validate
flamelet --task users          # Provision users
flamelet --task all            # Full deployment
```

---

## Key Principles

1. **`inventory.py` is required** — defines all hosts and SSH config
2. **`vars/__init__.py` is required** — defines users, groups, shell paths
3. **Services belong in `vars/`** — not in framework code
4. **Inheritance flows downward** — host-specific wins over location wins over global
5. **Self-contained configuration** — no imports from `core.operations`
6. **@local connector for testing** — CI can run `flamelet --dry` without SSH

---

## Using @local in CI

The `@local` connector lets you test the full pipeline in CI without SSH:

```bash
# In CI: use @local connector
PYTHONPATH=. TENANT_PATH=tenants/flamelet-example python -m core.cli --dry --task all

# This works without any SSH keys or external network
# Useful for validating config loading and operation dispatch
```

---

## Reference

- **Framework docs**: See `CLAUDE.md` in the framework root for all 20 operations
- **Quick start**: See `README.md` in the framework root
- **Test example**: See `tests/integration/test_example_tenant.py`

---

**This example is production-ready.** All hostnames, SSH keys, and credentials are placeholders.
Replace with your actual infrastructure details when deploying.
