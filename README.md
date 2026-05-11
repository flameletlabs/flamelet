# flamelet

**Infrastructure as Code for humans.** A Python/pyinfra framework for multi-tenant infrastructure automation.

Flamelet v2 is the successor to [flamelet v1](https://github.com/flameletlabs/flamelet-legacy) (shell/Ansible). It replaces Ansible playbooks with Python operations—keeping infrastructure code simple, testable, and programmable.

---

## Quick Start

```bash
# Install framelet
curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/install.sh | bash

# Configure a tenant
mkdir -p ~/src/my-infrastructure/tenants/production
# Add to ~/.config/flamelet/config.toml:
# [tenants]
# production = "~/src/my-infrastructure/tenants/production"

# Run provisioning
~/src/my-infrastructure/tenants/production/run.py --dry
~/src/my-infrastructure/tenants/production/run.py
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

See [DEVELOPMENT.md](DEVELOPMENT.md) for the complete guide. Quick version:

```bash
mkdir -p tenants/home
cp tenants/home/{__init__.py,inventory.py,vars.py,run.py} tenants/home/
```

Then:
1. **`inventory.py`** — Define your hosts and groups
2. **`vars.py`** — Provide users, groups, SSH keys, passwords
3. **`run.py`** — Import operations and call with tenant details

Register in `~/.config/flamelet/config.toml`:

```toml
[tenants]
home = "~/src/my-infrastructure/tenants/home"
```

Deploy:

```bash
~/src/my-infrastructure/tenants/home/run.py --dry --limit controller.work
~/src/my-infrastructure/tenants/home/run.py --task users
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

Framelet follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/):

```
~/.local/share/flamelet/    # Framework installation (code)
~/.config/flamelet/         # User configuration (config.toml, tenant registry)
~/.cache/flamelet/          # Temporary cache (reserved for future use)
```

Tenants can live anywhere (separate git repos). Register them in `config.toml` for easy discovery.

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
