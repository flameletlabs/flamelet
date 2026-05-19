# Contributing to Flamelet

Thanks for your interest in contributing! This guide covers development setup, workflows, testing, and adding new operations.

## Development Setup

```bash
# Clone the framework
git clone https://github.com/flameletlabs/flamelet.git
cd flamelet

# Install dependencies (requires Python 3.10+)
pip install -e ".[dev]"
# or with pipx:
pipx install --editable . --extra dev
```

## Development Guidelines

### ⚠️ MANDATORY: CI Verification After Every Push

**After every `git push`, verify the CI pipeline passes:**

```bash
# Check CI status
gh run list --limit 1 --json status,conclusion

# Expected output: Status: completed | Conclusion: success
```

**If CI fails:**
1. Review the failing job: `gh run view --json jobs`
2. Fix the issue (lint, tests, etc.)
3. Commit and push the fix
4. Verify CI passes again

**This prevents broken code from reaching main.**

### Code Quality

- **Linting:** `ruff check .` and `ruff format .`
- **Type hints:** Use Python type hints throughout
- **Tests:** Write tests for all new functionality
- **Docstrings:** Use clear docstrings for public APIs

### Testing Requirements

Run the complete test suite before submitting a PR:

```bash
# All tests
python3 -m pytest tests/ -v

# Unit tests only (no dependencies)
python3 -m pytest tests/unit/ -v

# Integration tests
python3 -m pytest tests/integration/ -v

# Specific test file
python3 -m pytest tests/unit/test_task_registry.py -v
```

## Adding a New Operation

New operations go in the **framework** (not tenant configs). Follow this pattern:

### 1. Create the operation

```python
# core/operations/myservice.py
def add_myservice_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy myservice to target hosts.
    
    Args:
        state: pyinfra State object
        hosts: pyinfra Inventory
        config: {hostname: {setting: value}}
        target_hosts: optional host list to limit deployment
        task: task name being run (for conditional logic)
    """
    targets = target_hosts if target_hosts else list(hosts)
    
    for host in targets:
        if host.name not in config:
            continue
        
        host_config = config[host.name]
        # Use add_op() to queue operations
        # See core/operations/ for examples
```

### 2. Register the operation

```python
# core/tasks/__init__.py, in _init_registry():
"myservice": [
    TaskEntry(add_myservice_ops, "MYSERVICE", "standard")
],
```

### 3. Add tests

```python
# tests/unit/test_myservice.py
from core.operations.myservice import add_myservice_ops

def test_myservice_ops_called():
    """Test that operation is dispatched correctly"""
    # Mock state, hosts, config and verify add_op calls
```

### 4. Update CLAUDE.md with usage examples

Add a section showing how tenant configs should use this operation.

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and write tests
3. Run tests locally: `pytest tests/`
4. Lint and format: `ruff check . && ruff format .`
5. Commit with clear messages
6. Push and verify CI passes
7. Open a PR with description of changes

## Documentation

- **CLAUDE.md** — Complete AI reference for generating tenant configs
- **README.md** — Framework overview and quick start
- **TESTING.md** — Comprehensive testing guide
- **docs/** — Additional reference documentation

See also: [tenants/flamelet-example/README.md](tenants/flamelet-example/README.md) for a complete example tenant.

## Questions?

Open an issue on GitHub or consult the docs directory for detailed references.
