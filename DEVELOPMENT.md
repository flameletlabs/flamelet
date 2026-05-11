# pyinfra-framework Development Guide

Instructions for AI and developers extending the framework.

## Architecture

```
core/                          # Framework (reusable across tenants)
├── runner.py                  # Orchestration: connect, add_ops, run, results
├── operations/
│   └── users.py               # Parameterized operations (groups, users)

tenants/home/                  # Home tenant (internal; template for new tenants)
├── inventory.py               # Host definitions, groups, SSH config
├── vars.py                    # Tenant-specific data (users, SSH keys, passwords)
└── run.py                     # Entry point: imports framework + tenant data

tests/                         # Framework-wide tests
├── conftest.py                # Shared pytest fixtures
├── test_core_users.py         # Framework operation tests
├── test_inventory.py          # Tenant inventory validation
└── test_integration.py        # SSH smoke tests
```

## Flexible Tenant Discovery

Framework can be located via multiple methods (in priority order):

1. **FRAMEWORK_ROOT environment variable** — Set explicitly:
   ```bash
   FRAMEWORK_ROOT=/path/to/framework ./tenants/my-infra/run.py
   ```

2. **Relative path** — Tenants at `framework/../tenants/my-infra/run.py`:
   ```bash
   ./tenants/my-infra/run.py  # Finds framework automatically
   ```

3. **Current working directory** — If `core/` exists in cwd:
   ```bash
   cd /path/to/framework && ./tenants/my-infra/run.py
   ```

4. **Search upward** — Searches parent directories for `core/` (max 10 levels)

Use `core.paths.setup_imports()` in tenant `run.py` for automatic discovery:
```python
from core.paths import setup_imports
setup_imports()  # Configures sys.path automatically

from core.operations.users import add_user_ops
```

## Creating a New Tenant

### Step 1: Create directory structure

```bash
mkdir -p tenants/my-infrastructure
cp tenants/home/{__init__.py,inventory.py,vars.py,run.py} tenants/my-infrastructure/
```

### Step 2: Edit `inventory.py`

Define hosts and groups:

```python
from pyinfra.api import Inventory

def build_inventory():
    return Inventory(
        (
            [
                ("host1.example.com", {"ssh_hostname": "10.0.0.1"}),
                ("host2.example.com", {"ssh_hostname": "10.0.0.2"}),
            ],
            {"ssh_user": "admin", "ssh_key": "~/.ssh/id_rsa"},
        ),
        prod=(["host1.example.com"], {"_doas": True}),
        staging=(["host2.example.com"], {}),
    )
```

**Groups:** Define OS-level groups (for privilege escalation) and location groups (for filtering):
- **OS groups** (`openbsd`, `freebsd`, `linux`) — carry `_doas`/`_sudo` config
- **Location groups** (`work`, `home`, `baar`, `prod`, `staging`) — inherit privilege config from OS groups

Groups allow targeting with `--limit group_name`. Example home tenant groups:
```python
# OS groups (privilege escalation)
openbsd=(["controller.work"], {"_doas": True}),
freebsd=(["virt.home", "virt-01.baar", ...], {"_sudo": True}),
# Location groups (no extra config — inherit from OS groups)
work=(["controller.work"], {}),
baar=(["virt-01.baar", "virt-02.baar", "virt-03.baar"], {}),
```

Usage:
```bash
./tenants/my-infra/run.py --dry --limit baar       # all baar hosts
./tenants/my-infra/run.py --dry --limit work       # work location only
./tenants/my-infra/run.py --dry --limit freebsd    # all FreeBSD hosts (OS group)
```

### Step 3: Edit `vars.py`

Define all tenant-specific details (no defaults in framework):

```python
# Framework is detail-agnostic — tenant provides all content

# System groups to create
GROUPS = ["syseng", "keep", "custom"]

# SSH keys, passwords, user configs, etc.
USERS = {
    "admin": {
        "comment": "Admin User",
        "password": "hashed_password",
        "groups": {"Alpine": "wheel", "Linux": "sudo", "FreeBSD": "wheel", "OpenBSD": "wheel"},
        "shell": {"Alpine": "/bin/sh", "Linux": "/bin/bash", "FreeBSD": "/usr/local/bin/bash", ...},
        "public_keys": ["ssh-rsa AAAA..."],
    },
}

CUSTOM_PACKAGES = ["vim", "git", "curl"]
```

### Step 4: Edit `run.py`

Import operations and call with tenant var details:

```python
from core.operations.users import add_user_ops
from core.operations.packages import add_packages  # Future

def add_ops(state, inventory, target_hosts=None, task="all"):
    # Pass tenant details to framework operations
    add_user_ops(
        state, 
        inventory, 
        users_config=tenant_vars.USERS,
        group_names=tenant_vars.GROUPS,  # Detail from tenant vars, not framework
        target_hosts=target_hosts,
        task=task,
    )
    # add_packages(state, inventory, packages=tenant_vars.CUSTOM_PACKAGES)
```

### Step 5: Test

```bash
./tenants/my-infrastructure/run.py --dry --limit host1.example.com
./tenants/my-infrastructure/run.py --limit prod --task users
```

## Framework Standard Tasks

All tenants inherit these standard tasks from `core/runner.py`:

| Task | Purpose | When to Run |
|------|---------|------------|
| `groups` | Create system groups (syseng, keep, etc.) | Before users |
| `users` | Create users + SSH keys + passwords | After groups |
| `sudo` | Configure NOPASSWD sudoers (Linux only) | After users, before switching to syseng user |
| `all` | All tasks combined (default) | Full provisioning |

**Tenant default:** No need to specify task_choices — framework standard is automatic.

To extend with custom tasks, pass additional choices to `build_parser()`:
```python
from core.runner import STANDARD_TASKS, build_parser

def main():
    parser = build_parser(task_choices=STANDARD_TASKS + ["packages", "services"])
```

## Adding a New Operation

### Step 1: Create operation module

New file: `core/operations/packages.py`

```python
"""Package management operations."""

from pyinfra.api.operation import add_op
from pyinfra.operations import apt, pacman

def add_packages(state, hosts, packages_config, target_hosts=None, task="all"):
    """Install packages on specified hosts.
    
    Args:
        state: pyinfra State object
        hosts: Inventory object
        packages_config: {"ubuntu": ["vim", "git"], "arch": ["vim", "git"]}
        target_hosts: list of Host objects to deploy to
        task: "all" (for compatibility with framework)
    """
    targets = target_hosts if target_hosts else list(hosts)
    
    for host in targets:
        os_type = host.get_fact(Os)
        
        # OS-specific package manager
        if os_type == "Linux":
            packages = packages_config.get("ubuntu", [])
            for pkg in packages:
                add_op(
                    state,
                    apt.packages,
                    name=f"Install {pkg}",
                    packages=[pkg],
                    host=host,
                )
```

### Step 2: Create tests

New file: `tests/test_packages.py`

```python
"""Tests for packages operation."""

import pytest
from core.operations.packages import add_packages

class TestPackages:
    def test_add_packages_queues_ops(self, mock_state, mock_inventory):
        """add_packages should queue install ops per package."""
        config = {"ubuntu": ["vim", "git"]}
        hosts = list(mock_inventory)
        add_packages(mock_state, mock_inventory, config)
        # Assert ops were queued
```

### Step 3: Register in tenant

Update `tenants/my-infrastructure/run.py`:

```python
from core.operations.packages import add_packages

def add_ops(state, inventory, target_hosts=None, task="all"):
    add_user_ops(...)
    if task in ("packages", "all"):
        add_packages(state, inventory, tenant_vars.PACKAGES, ...)
```

Update `build_parser(task_choices=["groups", "users", "packages", "all"])`.

### Step 4: Test

```bash
./tenants/my-infrastructure/run.py --task packages --dry
make test  # Verify new tests pass
```

## Testing Patterns

### Unit tests (no SSH)
- Test constants (BASH, SUDO_GROUP paths)
- Test inventory loading (host count, groups, SSH config)
- Test operation logic without SSH connection

**Run:** `make test`

### Lint
- Import sorting, unused imports, f-string warnings

**Run:** `make lint`

### Integration tests (requires SSH)
- Real SSH to a test host
- Use `--dry` to validate without changes
- Marked with `@pytest.mark.integration`

**Run:** `make integration`

**Example:**
```python
@pytest.mark.integration
def test_deploy_prod():
    result = subprocess.run(
        [PYTHON, "tenants/my-infrastructure/run.py", "--dry", "--limit", "prod"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "4/4 ops ok" in result.stdout
```

## Common Tasks

### Add a new host to tenant inventory

Edit `tenants/my-infrastructure/inventory.py`:

```python
all_hosts = [
    ("existing-host", {...}),
    ("new-host.example.com", {"ssh_hostname": "10.0.0.3"}),  # Add this
]
```

### Add a new SSH key to a user

Edit `tenants/my-infrastructure/vars.py`:

```python
USERS = {
    "admin": {
        "public_keys": [
            "ssh-rsa AAAA...",
            "ssh-rsa BBBB...",  # Add this
        ],
    },
}
```

### Add a new operation task to the CLI

1. Create operation: `core/operations/new_op.py`
2. Import in tenant: `from core.operations.new_op import add_new_op`
3. Call in `add_ops()` function
4. Update `build_parser(task_choices=[..., "new_op", ...])`
5. Add tests: `tests/test_new_op.py`

### Run on a single host

```bash
./tenants/my-infrastructure/run.py --limit host1.example.com
```

### Run with verbose debug output

```bash
./tenants/my-infrastructure/run.py --verbose -v --dry
```

### Validate inventory without deploying

```bash
./tenants/my-infrastructure/run.py --dry
```

## Key Design Principles

1. **Framework is detail-agnostic** — Core tasks (groups, users, sudo) have no built-in defaults
2. **Tenant provides all details** — GROUPS, USERS, SSH keys, passwords all in `vars.py`
3. **Operations are parameterized** — Accept config from tenant (users_config, group_names, etc.)
4. **Framework defines mechanism** — Tasks and operations; tenant defines content
5. **Tests cover framework** — Unit tests in `tests/test_core_*.py`
6. **Inventory validates tenant** — Tests in `tests/test_inventory.py` validate tenant structure
7. **Integration tests optional** — Marked with `@pytest.mark.integration`, skipped by default

## User Provisioning Best Practices

**Bootstrap users:**
- **Debian/Linux:** Use `debian` user for fresh VM bootstrap (has NOPASSWD sudo)
- **FreeBSD:** Use `root` for fresh jails (or `syseng` if already configured)
- **OpenBSD:** Use `syseng` (configured at VM setup)

**Shell defaults:**
- **Default shell for NEW users:** bash (Linux: `/bin/bash`, BSD: `/usr/local/bin/bash`)
- **Never modify existing users** — Leave root and system users with their default shells
- Root shell should always remain as system default to avoid breaking system tools

**Sudoers NOPASSWD:**
- Configure only on Linux hosts with `_sudo: True`
- FreeBSD wheel group already works without password
- Use `--task sudo` to provision NOPASSWD entries

**Workflow (fresh host):**
```bash
# 1. Bootstrap with OS user (debian, root, or syseng)
./tenants/my-infra/run.py --task users

# 2. Configure NOPASSWD sudo (Linux only)
./tenants/my-infra/run.py --task sudo

# 3. Update inventory to use syseng user for future runs
# Edit tenants/my-infra/inventory.py: remove bootstrap ssh_user override
```

## Extending core/runner.py

If you need to modify core deployment orchestration:

1. Framework change must work for ALL tenants
2. Backward-compatible with existing `add_ops()` signature
3. Update tests in `tests/test_core_*.py`
4. Test with home tenant: `./tenants/home/run.py --dry`

## File Modification Reference

| Task | File | Change |
|------|------|--------|
| Add tenant | `tenants/my-infra/` | Create directory, copy template files |
| Add operation | `core/operations/new.py` | New module with parameterized functions |
| Add user config | `tenants/my-infra/vars.py` | Extend USERS dict |
| Add host | `tenants/my-infra/inventory.py` | Add tuple to hosts list |
| Add CLI flag | `tenants/my-infra/run.py` | Update `build_parser()` call |
| Add task type | `core/runner.py` | Extend task dispatch logic |
| Add test | `tests/test_*.py` | New test class or function |

## Debugging

### SSH connection issues

```bash
./tenants/my-infrastructure/run.py --verbose --dry --limit host1
# Shows [DEBUG] Connected to 1 hosts (or failed_hosts)
```

### Operation not running

```bash
./tenants/my-infrastructure/run.py --task groups --dry --verbose
# Shows [DEBUG] Operations queued and actual ops executed
```

### Test failures

```bash
make test -- -v -s tests/test_inventory.py::TestTenantInventory::test_host_count
# Verbose output with print statements
```

---

**Last updated:** 2026-05-10  
**Framework version:** 0.1.0
