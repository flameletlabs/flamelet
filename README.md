# flamelet

**Infrastructure as Code for humans.** A Python/pyinfra framework for multi-tenant infrastructure automation.

Flamelet v2 is the successor to [flamelet v1](https://github.com/flameletlabs/flamelet-legacy) (shell/Ansible). It replaces Ansible playbooks with Python operations—keeping infrastructure code simple, testable, and programmable.

---

## Quick Start

```bash
# Install flamelet
pip install -e ~/src/floads/flamelet

# Create your first tenant (XDG-compliant)
mkdir -p ~/.config/flamelet/tenants/production/vars/{location,hosts}

# Create inventory.py and vars/__init__.py (see examples below)
# Then run provisioning with the flamelet CLI (no run.py needed!)
flamelet --dry
flamelet --task users
flamelet --limit app.example.com --task all
```

---

## What is flamelet?

Flamelet is an **infrastructure automation framework** built on [pyinfra](https://pyinfra.com) that brings:

- **Multi-tenant architecture** — manage multiple infrastructure projects independently
- **Python operations** — infrastructure code in Python, not YAML
- **Detail-agnostic framework** — the framework provides mechanism; tenants provide content
- **OS-aware automation** — Linux, FreeBSD, OpenBSD with native privilege escalation
- **Dry-run first** — test before applying changes (`--dry` flag)
- **Task-based deployment** — run specific tasks (groups, users, sudo, etc.)

Example: provision users with SSH keys and NOPASSWD sudoers in **10 lines of Python**:

```python
from core.operations.users import add_user_ops
from core.operations.sudo import add_sudoers_ops

def add_ops(state, inventory, target_hosts=None, task="all"):
    add_user_ops(state, inventory, 
        users_config=USERS,      # From tenant vars
        group_names=GROUPS,
        target_hosts=target_hosts, task=task)
    if task in ("sudo", "all"):
        add_sudoers_ops(state, inventory, users_config=USERS)
```

No YAML. No roles. No handlers. Just Python.

---

## Installation

### Prerequisites

- **Python 3.8+** (3.11+ recommended)
- **Git**
- **pip** or **pipx** (for isolated pyinfra environment)

### Install via curl

```bash
curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/install.sh | bash
```

The installer will:
1. Clone framelet to `~/.local/share/flamelet/`
2. Create config scaffold at `~/.config/flamelet/config.toml`
3. Install `pyinfra` and test tools via `pipx`

### Install from source (development)

```bash
git clone https://github.com/flameletlabs/flamelet.git
cd flamelet
git checkout refactor/python-pyinfra  # (or main after v2.0 release)
pip install pyinfra pytest ruff
```

---

## Creating Your First Tenant

Tenants live in `~/.config/flamelet/tenants/<name>/` (XDG-compliant) and are automatically discoverable by the `flamelet` CLI.

**Tenant Structure** (no `run.py` needed anymore!):

```
~/.config/flamelet/tenants/production/
├── inventory.py              # Required: host definitions
└── vars/
    ├── __init__.py           # Required: users, groups, constants
    ├── all.py                # Optional: global defaults
    ├── location/
    │   └── production.py      # Optional: location-specific overrides
    └── hosts/
        └── app_prod_example_com.py  # Optional: host-specific configs
```

### inventory.py (Required)

```python
from pyinfra.inventory import Inventory

def build_inventory():
    return Inventory(
        ssh_hosts={
            "app.example.com": {"groups": ["web"]},
            "db.example.com": {"groups": ["db"]},
        },
        groups={"web": ["app.example.com"], "db": ["db.example.com"]},
    )
```

### vars/__init__.py (Required)

```python
USERS = {
    "deploy": {
        "comment": "Deployment user",
        "password": "$6$...",  # sha-512 hash
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

### vars/all.py (Optional - Global Defaults)

```python
PACKAGES = {
    "Linux": ["curl", "git", "htop"],
    "FreeBSD": ["curl", "git", "htop"],
}

WIREGUARD = {}  # Optional: add here if deploying WireGuard
MONIT = {}      # Optional: add here if deploying Monit
```

### vars/location/{location}.py (Optional - Location-Specific)

For hostname `app.production.example.com`, create `vars/location/production.py`:

```python
MONIT = {
    "app.production.example.com": {
        "daemon": 120,
        "checks": {...}
    }
}
```

### vars/hosts/{hostname}.py (Optional - Host-Specific)

For hostname `app.example.com`, create `vars/hosts/app_example_com.py`:

```python
MONIT = {
    "app.example.com": {
        "daemon": 120,
        "checks": {...}
    }
}
```

### Deploy

```bash
# Test before applying (dry-run)
flamelet --dry

# Deploy to specific host
flamelet --limit app.example.com --dry

# Run specific task
flamelet --task monit

# Deploy for real
flamelet
```

No `run.py` needed! The framework `flamelet` CLI automatically discovers your tenant.

---

## Available Tasks (20+)

All tenants support these framework tasks via `flamelet --task <task>`:

| Task | Config Attribute | Purpose |
|------|------------------|---------|
| `users` | — | User/group provisioning |
| `sudo` | — | Sudoers configuration |
| `packages` | PACKAGES | Package installation (OS-keyed) |
| `sysctl` | SYSCTL | Kernel parameter tuning |
| `services` | SERVICES | Service management |
| `autossh` | AUTOSSH_TUNNELS, AUTOSSH_GATEWAY | SSH reverse tunnels |
| `wireguard` | WIREGUARD | WireGuard VPN configuration |
| `unbound` | UNBOUND | DNS resolver (Unbound) |
| `monit` | MONIT | Process monitoring (Monit) |
| `opensmtpd` | OPENSMTPD | Mail relay (OpenSMTPD) |
| `pf` | PF | Firewall rules (BSD pf) |
| `docker` | DOCKER | Docker installation & config |
| `node_exporter` | NODE_EXPORTER | Prometheus node exporter |
| `k3s` | K3S | Kubernetes (k3s) cluster |
| `virtualization` | VIRTUALIZATION | VMs & jails (bhyve/Bastille) |
| `storage` | STORAGE | Storage (ZFS/NFS/SMB) |
| `nginx` | NGINX | Reverse proxy (nginx) |
| `postgresql` | POSTGRESQL | PostgreSQL database |
| `prometheus` | PROMETHEUS | Metrics server (Prometheus) |
| `registry` | REGISTRY | Container registry |

Run `flamelet --help` to see available tasks for your tenant.

---

## OS Support

| OS | Privilege Escalation | Shell |
|----|---------------------|-------|
| **Linux** (Debian, Alpine, etc.) | `sudo` with NOPASSWD sudoers | `/bin/bash` or `/bin/sh` |
| **FreeBSD** | `sudo` (wheel group, no password) | `/usr/local/bin/bash` |
| **OpenBSD** | `doas` (built-in) | `/usr/local/bin/bash` |

---

## Framework Architecture

### Framework (Reusable Code)

Located in `/src/floads/flamelet/` (or `~/.local/share/flamelet/` when installed):

```
core/
├── tasks/                  # Task registry & config loaders
│   ├── __init__.py        # TASK_REGISTRY (maps task → operation)
│   └── loader.py          # 3-tier config loading (all < location < host)
├── operations/            # 20+ operations (monit, wireguard, docker, k3s, etc.)
├── cli.py                 # CLI entry point (flamelet command)
├── runner.py              # Deployment orchestrator
├── paths.py               # XDG path discovery
└── config.py              # Configuration
```

### Tenant (Configuration + Inventory)

Located in `~/.config/flamelet/tenants/<name>/`:

```
<tenant>/
├── inventory.py           # Host definitions
└── vars/                  # Configuration (no logic!)
    ├── __init__.py       # Users, groups, constants
    ├── all.py            # Global defaults
    ├── location/         # Location-specific overrides
    └── hosts/            # Host-specific configs
```

### XDG Compliance

Flamelet follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/):

```
~/.local/share/flamelet/              # Framework code (installed)
~/.config/flamelet/                   # User configuration
  └── tenants/
      └── <tenant-name>/              # Tenant config (automatically discovered)
          ├── inventory.py            # Required
          └── vars/                   # Required
              ├── __init__.py         # Required
              ├── all.py              # Optional: global defaults
              ├── location/           # Optional: location-specific
              └── hosts/              # Optional: host-specific
~/.cache/flamelet/                    # Reserved for future use
```

### Discovery Process

**Framework Discovery:**
1. `FRAMEWORK_ROOT` environment variable (if set)
2. `~/.local/share/flamelet/` (installed location)
3. Parent directories (local development)
4. Current working directory

**Tenant Discovery:**
1. `TENANT_PATH` environment variable (if set)
2. `~/.config/flamelet/tenants/` (XDG-compliant, auto-discovered)
3. Current working directory (if it's a tenant directory)

**Usage:**
```bash
# Automatic discovery (from tenant directory)
cd ~/.config/flamelet/tenants/production
flamelet --task monit

# Explicit paths
FRAMEWORK_ROOT=~/src/floads/flamelet TENANT_PATH=~/.config/flamelet/tenants/production \
  flamelet --task monit

# Environment override
export FRAMEWORK_ROOT=~/src/floads/flamelet
export TENANT_PATH=~/.config/flamelet/tenants/production
flamelet --task monit
```

---

## Testing

Flamelet includes a comprehensive test suite:

```bash
# Unit tests (no SSH, no real hosts)
python3 -m pytest tests/unit/ -v

# Integration tests (requires SSH access to real hosts)
python3 -m pytest tests/integration/ -v

# All tests
python3 -m pytest tests/ -v

# Specific test file
python3 -m pytest tests/unit/test_tasks.py -v
```

See `tests/` for test structure and examples.

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — Framework reference for AI assistants & detailed implementation guide
- **[README.md](README.md)** — This file: quick start, architecture overview, usage
- **`core/tasks/__init__.py`** — TASK_REGISTRY source code (all available tasks)
- **`core/operations/`** — Each operation module has detailed docstrings

### For AI Assistants

The framework is fully documented for AI-driven infrastructure generation:

```python
# AI can read CLAUDE.md to understand:
# - Operation signatures and config requirements
# - 3-tier configuration inheritance
# - How to add new operations
# - Best practices for tenant configs

# Then generate complete tenant configs including:
# - inventory.py with realistic hosts
# - vars/__init__.py with users and groups
# - vars/all.py with global package lists
# - vars/location/{location}.py with environment-specific configs
# - vars/hosts/{host}.py with host-specific services
```

See **CLAUDE.md** for the full AI-friendly reference.

---


## License

MIT — See [LICENSE](LICENSE)

---

**Built with [pyinfra](https://pyinfra.com)**
