# Contributing to Flamelet

Thanks for your interest in contributing! This guide covers development workflows, testing, and adding new operations.

---

## Development Setup

```bash
# Clone the framework
git clone https://github.com/flameletlabs/flamelet.git
cd flamelet
git checkout refactor/python-pyinfra  # (or main after v2.0)

# Install dependencies
pip install pyinfra pytest ruff
# or with pipx:
pipx install pyinfra
pipx inject pyinfra pytest ruff
```

---

## Code Style

Use **ruff** for linting:

```bash
make lint          # Check style
ruff check . --fix # Auto-fix
```

Standards:
- Line length: 100 characters
- Python 3.11+ (target)
- Minimal comments (only WHY, not WHAT)
- No TODO/FIXME comments (open issues instead)

---

## Testing

### Unit Tests (no SSH)

```bash
make test          # Run all unit tests
pytest tests/test_users.py -v
pytest tests/ -k "test_bash" -v
```

Unit tests mock SSH and pyinfra State. No real infrastructure touched.

### Lint

```bash
make lint
```

### Integration Tests (requires SSH)

```bash
make integration   # Runs tests marked @pytest.mark.integration
```

These tests run against live hosts with `--dry` flag. Requires SSH access to test infrastructure.

---

## Adding a New Operation

Operations are reusable functions that manage infrastructure (users, packages, services, etc.). Follow this pattern:

### 1. Create the operation module

New file: `core/operations/packages.py`

```python
"""Package installation operations."""

from pyinfra.api.operation import add_op
from pyinfra.operations import apt
from pyinfra.facts.server import Kernel

def add_packages(state, hosts, packages_config, target_hosts=None, task="all"):
    """Install packages on specified hosts.
    
    Args:
        state: pyinfra State object
        hosts: Inventory object
        packages_config: {"ubuntu": ["vim", "git"], "arch": [...]}
        target_hosts: list of Host objects to deploy to
        task: "all" (for framework compatibility)
    """
    targets = target_hosts if target_hosts else list(hosts)
    
    for host in targets:
        os_key = host.get_fact(Kernel)
        packages = packages_config.get(os_key, [])
        
        for pkg in packages:
            add_op(
                state,
                apt.packages,
                name=f"Install {pkg} on {host.name}",
                packages=[pkg],
                host=host,
            )
```

**Key points:**
- Take `state`, `hosts`, config dict, optional `target_hosts`, optional `task`
- Use `host.get_fact(Kernel)` for OS detection
- Call `add_op()` for each operation
- No side effects — only queue operations

### 2. Write tests

New file: `tests/test_packages.py`

```python
"""Tests for package operations."""

import pytest
from core.operations.packages import add_packages

def test_add_packages_ubuntu(mock_state, mock_inventory):
    """add_packages should queue apt install ops."""
    config = {"Linux": ["vim", "git"]}
    hosts = list(mock_inventory)
    
    with patch("pyinfra.api.host.Host.get_fact", return_value="Linux"):
        add_packages(mock_state, hosts, config)
    
    # Assert ops queued (2 packages × hosts)
    total = sum(len(ops) for ops in mock_state.ops.values())
    assert total == 2 * len(hosts)
```

**Patterns:**
- Mock `Host.get_fact()` to test OS-specific logic
- Check operation count, not SSH execution
- Test per-OS branches separately

### 3. Register in tenant

Update `tenants/my-infra/run.py`:

```python
from core.operations.packages import add_packages

def add_ops(state, inventory, target_hosts=None, task="all"):
    add_user_ops(...)
    if task in ("packages", "all"):
        add_packages(state, inventory, tenant_vars.PACKAGES, target_hosts, task)

def main():
    parser = build_parser(task_choices=["groups", "users", "packages", "all"])
    ...
```

### 4. Test locally

```bash
make test          # Unit tests pass
make lint          # Style check
./tenants/my-infra/run.py --dry --task packages
```

---

## Framework vs. Tenant Code

**Framework (`core/`):**
- Provides operations (users, groups, sudo, etc.)
- Mechanism, not policy
- No defaults for content (no hardcoded groups, users, packages)
- Tested in `tests/test_core_*.py`
- Published to PyPI (future)

**Tenant code:**
- Lives in separate repos (e.g., `my-infrastructure/tenants/home/`)
- Provides all details (GROUPS, USERS, SSH keys, passwords)
- Calls framework operations with tenant-specific config
- Can add custom operations
- Can define custom tasks

**Example:** Framework defines `add_user_ops()`, tenant provides `USERS` dict with actual users.

---

## Pull Request Guidelines

1. **Branch naming:** `feature/operation-name`, `fix/issue-123`, `docs/update-readme`
2. **Commits:** One logical change per commit; clear messages ("Add package operation, test OS-specific paths")
3. **Tests:** New features require tests (unit + integration if applicable)
4. **Linting:** `make lint` must pass
5. **Description:** Explain WHY, not just WHAT

---

## Reporting Issues

Use GitHub Issues with:
- **Title:** One-line summary
- **Reproduction:** Steps to reproduce (if bug)
- **Expected:** What should happen
- **Actual:** What actually happens
- **Environment:** OS, Python version, flamelet version

---

## Documentation

- **DEVELOPMENT.md** — Guide for operators and developers
- **README.md** — User-facing quick start and overview
- **Docstrings** — One-line explanation of WHY, not WHAT
- **Comments** — Only non-obvious invariants or workarounds

---

## Architecture

See [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Flexible path discovery strategies
- XDG Base Directory structure
- Multi-tenant configuration
- Standard framework tasks
- User provisioning best practices

---

## Questions?

Open an issue or discuss in the repository. Flamelet is actively maintained and welcomes feedback.
