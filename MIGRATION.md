# Migrating from flamelet v1 to v2

Flamelet v2 is a complete rewrite: from bash/Ansible to Python/pyinfra. This guide helps you upgrade
your infrastructure from v1 to v2.

---

## What Changed

### Language & Framework
- **v1:** Shell scripts (bash) + Ansible playbooks + Galaxy roles
- **v2:** Python code (pyinfra operations) — no Ansible, no Galaxy

### Invocation
- **v1:** `flamelet -t <tenant> -l ansible` (run Ansible playbook)
- **v2:** `flamelet --task <task> --limit <host>` (run pyinfra operations)

### Tenant Structure
- **v1:** `~/.flamelet/tenant/flamelet-<name>/` with `config.sh` + Ansible playbooks
- **v2:** `~/.config/flamelet/tenants/<name>/` with Python files (XDG-compliant)

### Configuration
- **v1:** Shell variables in `config.sh`, Ansible vars in `group_vars/` and `host_vars/`
- **v2:** Python dicts in `vars/__init__.py`, `vars/all.py`, `vars/location/`, `vars/hosts/`

### Operations
- **v1:** Ansible playbooks + tasks + roles (YAML)
- **v2:** Python functions in `core/operations/*.py` — one function per service

---

## Step-by-Step Migration

### Step 1: Install flamelet v2

Clone the v2 framework and install dependencies:

```bash
git clone https://github.com/flameletlabs/flamelet.git ~/src/flamelet
cd ~/src/flamelet
pip install -e .
flamelet --help
```

Or if you prefer not to install system-wide:

```bash
PYTHONPATH=~/src/flamelet python3 -m core.cli --help
```

### Step 2: Create the tenant directory structure

Create the v2 tenant directory (XDG-compliant):

```bash
mkdir -p ~/.config/flamelet/tenants/<your-tenant>/vars/{location,hosts}
cd ~/.config/flamelet/tenants/<your-tenant>
```

Replace `<your-tenant>` with your tenant name (e.g., `production`, `staging`, `home`).

### Step 3: Create `inventory.py` from your v1 host list

In your v1 `config.sh`, you likely defined a host list or an Ansible inventory file. Create an
`inventory.py` file with your hosts:

**v1 example (config.sh):**
```bash
CFG_ANSIBLE_INVENTORY="inventories/hosts.yml"
```

**v2 equivalent (inventory.py):**
```python
from pyinfra.api.inventory import Inventory

def build_inventory():
    return Inventory(
        (
            [
                ("app.example.com", {"ssh_hostname": "192.168.1.10"}),
                ("db.example.com", {"ssh_hostname": "192.168.1.20"}),
            ],
            {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"},
        ),
        web=(["app.example.com"], {}),
        db=(["db.example.com"], {}),
    )
```

### Step 4: Create `vars/__init__.py` with users and system config

This file defines users, groups, shell paths, and sudoers configuration:

```python
# vars/__init__.py

USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": "$6$...",  # sha-512 hash from mkpasswd --method=sha-512
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

### Step 5: Create `vars/all.py` with global defaults

This file contains default configurations that apply to all hosts:

```python
# vars/all.py

PACKAGES = {
    "Linux": ["curl", "git", "htop", "openssh-server"],
    "FreeBSD": ["curl", "git", "htop"],
}

# Add service configs if applicable
WIREGUARD = {}  # If any hosts use WireGuard
MONIT = {}      # If any hosts use Monit
DOCKER = {}     # If any hosts run Docker
# ... other services
```

### Step 6: Create `vars/location/{location}.py` (optional)

For location-specific configurations. Location is extracted from hostname (last dot segment):
- `app.prod.home` → location `home`
- `db.staging.example.com` → location `example.com`

```python
# vars/location/home.py

MONIT = {
    "app.home": {
        "daemon": 120,
        "checks": {
            "system": "check system app.home\n  if memory usage > 75% then alert",
        }
    }
}
```

### Step 7: Create `vars/hosts/{hostname}.py` (optional)

For host-specific configurations. Filename format: `<hostname>` with `.` and `-` replaced by `_`:

```python
# vars/hosts/app_home.py

WIREGUARD = {
    "app.home": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.2/24",
                "port": 51820,
                "private_key": "...",
            }
        }
    }
}
```

### Step 8: Test your configuration

Validate that your tenant is correctly configured by running a dry-run:

```bash
# From the tenant directory
flamelet --dry --task users

# Or with explicit paths
PYTHONPATH=~/src/flamelet \
TENANT_PATH=~/.config/flamelet/tenants/<your-tenant> \
python3 -m core.cli --dry --task users
```

You should see operations queued without errors.

### Step 9: Run a single task

Start by running a simple task (users) to verify connectivity:

```bash
flamelet --task users --dry --limit app.example.com
```

Once confirmed, remove `--dry` to apply changes.

---

## Configuration Reference

For complete documentation of all 20 operations and their configuration attributes, see the
v2 [CLAUDE.md](../../blob/main/CLAUDE.md) file in the `main` branch.

Key operations available in v2:
- `users` — user and group provisioning
- `packages` — package installation
- `monit` — process monitoring
- `wireguard` — VPN configuration
- `docker` — container runtime
- `kubernetes` (k3s) — Kubernetes cluster
- `postgresql` — database
- `nginx` — reverse proxy
- ... and 12 more

---

## Troubleshooting

### "Tenant inventory.py not found"
Ensure your tenant directory exists at `~/.config/flamelet/tenants/<name>/` and contains `inventory.py`.

### "PYTHONPATH error"
If `flamelet` command is not available, set PYTHONPATH:
```bash
PYTHONPATH=~/src/flamelet python3 -m core.cli --help
```

### SSH connection errors
Check that your SSH key and username match the `Inventory` object in `inventory.py`. For debugging:
```bash
flamelet --verbose --task users --dry
```

### Config loading issues
Validate your `vars/__init__.py` syntax:
```bash
python3 -c "import sys; sys.path.insert(0, '~/.config/flamelet/tenants/<name>'); from vars import *; print('OK')"
```

---

## Support

For detailed operation reference, see:
- v2 [CLAUDE.md](../../blob/main/CLAUDE.md) — all operations with config examples
- v2 [TESTING.md](../../blob/main/TESTING.md) — how to run tests
- v2 [README.md](../../blob/main/README.md) — quick start and overview
