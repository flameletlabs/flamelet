# flamelet

**Infrastructure as Code for humans.** A Python/pyinfra framework for multi-tenant infrastructure automation.

Flamelet v2 is the successor to [flamelet v1](https://github.com/flameletlabs/flamelet-legacy) (shell/Ansible). It replaces Ansible playbooks with Python operations—keeping infrastructure code simple, testable, and programmable.

---

## Quick Start

```bash
# Install flamelet
curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/install.sh | bash

# Create your first tenant (XDG-compliant)
mkdir -p ~/.config/flamelet/tenants/production/vars/{location,hosts}

# Copy template from installed framework
cp ~/.local/share/flamelet/tenants/home/run.py ~/.config/flamelet/tenants/production/
cp ~/.local/share/flamelet/tenants/home/inventory.py ~/.config/flamelet/tenants/production/
cp ~/.local/share/flamelet/tenants/home/vars/*.py ~/.config/flamelet/tenants/production/vars/

# Edit to match your infrastructure
# Then run provisioning
~/.config/flamelet/tenants/production/run.py --dry
~/.config/flamelet/tenants/production/run.py
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

Tenants live in `~/.config/flamelet/tenants/<name>/` (XDG-compliant) and are automatically discoverable.

See [DEVELOPMENT.md](DEVELOPMENT.md) for the complete guide. Quick version:

```bash
# Create tenant directory
mkdir -p ~/.config/flamelet/tenants/home/vars/{location,hosts}

# Copy template files
cp core/tenants/home/{run.py,inventory.py} ~/.config/flamelet/tenants/home/
cp core/tenants/home/vars/*.py ~/.config/flamelet/tenants/home/vars/
```

Then edit:
1. **`inventory.py`** — Define your hosts and groups
2. **`vars/__init__.py`** — Provide users, groups, SSH keys, passwords  
3. **`vars/all.py`** — Global defaults (packages, sysctl, services)
4. **`vars/location/*.py`** — Location-specific overrides
5. **`vars/hosts/*.py`** — Per-host custom configs
6. **`run.py`** — Import operations and call with tenant details

Deploy:

```bash
# Test before applying (dry-run)
~/.config/flamelet/tenants/home/run.py --dry --limit controller.work

# Run specific tasks
~/.config/flamelet/tenants/home/run.py --task users
~/.config/flamelet/tenants/home/run.py --task packages

# Run all tasks
~/.config/flamelet/tenants/home/run.py
```

---

## Standard Tasks

All tenants support these framework-standard tasks:

| Task | Purpose |
|------|---------|
| `groups` | Create system groups (syseng, keep, etc.) |
| `users` | Create users + SSH keys + passwords |
| `sudo` | Configure NOPASSWD sudoers (Linux only) |
| `all` | All tasks combined (default) |

Run `./run.py --help` to see available tasks for your tenant.

---

## OS Support

| OS | Privilege Escalation | Shell |
|----|---------------------|-------|
| **Linux** (Debian, Alpine, etc.) | `sudo` with NOPASSWD sudoers | `/bin/bash` or `/bin/sh` |
| **FreeBSD** | `sudo` (wheel group, no password) | `/usr/local/bin/bash` |
| **OpenBSD** | `doas` (built-in) | `/usr/local/bin/bash` |

---

## XDG Base Directory Compliance

Flamelet follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/):

```
~/.local/share/flamelet/              # Framework installation (code)
~/.config/flamelet/                   # User configuration
  ├── config.toml                     # Tenant registry (optional)
  └── tenants/
      └── <tenant-name>/              # Tenant configuration (discoverable)
          ├── run.py                  # Entry point
          ├── inventory.py            # Host definitions
          └── vars/                   # Configuration data
              ├── all.py              # Global defaults
              ├── location/            # Location-specific overrides
              └── hosts/               # Per-host custom configs
~/.cache/flamelet/                    # Temporary cache (reserved for future use)
```

**Framework discovery:** Flamelet searches for the core/ directory in:
1. `FRAMEWORK_ROOT` environment variable (if set)
2. `~/.local/share/flamelet/` (XDG-compliant installation)
3. Parent directories (local development)

**Tenant discovery:** Tenants are looked up in:
1. `~/.config/flamelet/tenants/<name>/` (XDG-compliant, preferred)
2. Paths registered in `~/.config/flamelet/config.toml` (custom locations)

---

## Testing

Framelet includes a complete test suite:

```bash
make test          # Unit tests (no SSH)
make lint          # Code style check
make integration   # Integration tests (requires SSH)
```

---

## Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** — Complete guide for developers and operators
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to add operations and contribute

---

## Migration from Flamelet v1

If you're using the original shell/Ansible flamelet, see [flamelet-legacy](https://github.com/flameletlabs/flamelet-legacy) for the archived v1 repository. 

Key differences in v2:
- Python operations instead of Ansible playbooks
- `pyinfra` instead of `ansible`
- XDG-compliant paths
- Streamlined multi-tenant configuration

---

## License

MIT — See [LICENSE](LICENSE)

---

**Built with [pyinfra](https://pyinfra.com)**
