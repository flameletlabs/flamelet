# Flamelet Testing Guide

Complete test suite with 146 passing tests covering:
- TASK_REGISTRY initialization and structure (10 tests)
- 3-tier config inheritance (13 tests)
- OS-keyed package loading (6 tests)
- Tenant discovery and loading (7 tests)
- CLI function building (6 tests)
- Configuration loading during deployment (6 tests)
- Plus additional unit and integration tests

## Running Tests

### All Tests
```bash
cd ~/src/floads/flamelet
python3 -m pytest tests/ -v
```

### Unit Tests Only (No Dependencies)
```bash
python3 -m pytest tests/unit/ -v
```

### Integration Tests
```bash
python3 -m pytest tests/integration/ -v
```

### Specific Test File
```bash
python3 -m pytest tests/unit/test_tasks.py -v
python3 -m pytest tests/unit/test_loaders.py -v
python3 -m pytest tests/unit/test_cli.py -v
```

### Single Test
```bash
python3 -m pytest tests/unit/test_tasks.py::TestTaskRegistry::test_registry_initialized -v
```

### With Output Capture
```bash
python3 -m pytest tests/ -v -s  # Show print statements
```

### With Detailed Tracebacks
```bash
python3 -m pytest tests/ -v --tb=long
```

### Stop on First Failure
```bash
python3 -m pytest tests/ -x  # Exit on first failure
python3 -m pytest tests/ -x -v
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures & setup
├── unit/
│   ├── test_tasks.py          # TASK_REGISTRY tests (10 tests)
│   ├── test_loaders.py        # Config loader tests (13 tests)
│   └── test_cli.py            # CLI discovery tests (6 tests)
├── integration/
│   └── test_deployment.py     # Config loading tests (6 tests)
└── fixtures/                   # Mock tenant data
```

## Test Categories

### Unit Tests (35 tests)

#### TASK_REGISTRY Tests (`test_tasks.py`)
- Registry initialization and structure
- Required tasks presence
- TaskEntry validation
- Config attribute correctness
- Special cases (users, packages, autossh)
- Operation function importability

#### Config Loader Tests (`test_loaders.py`)
- 3-tier inheritance: all.py < location/*.py < hosts/*.py
- Merging of configurations
- Per-host packages loading
- OS-keyed package lists
- Location extraction from hostname
- Deduplication of packages
- Error handling for missing files

#### CLI Tests (`test_cli.py`)
- Inventory.py loading
- vars/__init__.py loading
- add_ops function building
- Function signature validation
- Unknown task handling

### Integration Tests (6 tests)

#### Config Loading Tests (`test_deployment.py`)
- MONIT config loading
- PACKAGES config loading
- Inventory loading
- Vars module loading
- add_ops function building
- 3-tier inheritance during loading

## Fixtures

All tests use pytest fixtures from `conftest.py`:

- **`tmp_tenant_dir`**: Temporary tenant directory with all required files
  - `inventory.py` with 3 mock hosts
  - `vars/__init__.py` with users, groups, constants
  - `vars/all.py` with PACKAGES, MONIT, WIREGUARD
  - `vars/location/` and `vars/hosts/` directories

- **`mock_inventory`**: pyinfra Inventory with 2 test hosts

- **`mock_state`**: pyinfra State (dry-run mode)

- **`mock_host`**: Mocked Host object

## What Gets Tested

### ✅ TASK_REGISTRY
- All 20 tasks are registered
- Each task has valid TaskEntry objects
- Config attributes are correct
- Operation functions are importable
- Special cases (users, sudo, packages, autossh) work correctly

### ✅ Config Loading (3-Tier Inheritance)
- Configs load from `vars/all.py` (global defaults)
- Configs load from `vars/location/{location}.py` (environment-specific)
- Configs load from `vars/hosts/{hostname}.py` (host-specific)
- Configs correctly merge: `all < location < host`
- Merging is deep (per-hostname)
- Location extraction from hostname works correctly
- Missing files don't cause errors
- OS-keyed packages deduplicate correctly

### ✅ Tenant Discovery
- `inventory.py` is loaded correctly
- `inventory.build_inventory()` is called
- `vars/__init__.py` is loaded correctly
- Required attributes (USERS, GROUPS, BASH, SUDO_GROUP) exist

### ✅ CLI Functions
- `add_ops()` is built correctly
- It accepts the right parameters
- It handles unknown tasks gracefully
- Function signature matches expectations

### ⏭️ NOT Tested (By Design)
- Actual SSH connections (would require real hosts)
- Actual operations execution (would change system state)
- Framework installation
- Interactive CLI parsing (covered by pyinfra's test suite)

## Test Coverage

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| TASK_REGISTRY | ✅ | 10 | All tasks, entries, attributes validated |
| Config Loaders | ✅ | 13 | 3-tier inheritance, merging, deduplication |
| Tenant Discovery | ✅ | 7 | inventory.py, vars/__init__.py loading |
| add_ops Building | ✅ | 6 | Function signature, parameter handling |
| Config Loading | ✅ | 6 | MONIT, PACKAGES, WIREGUARD loading |
| Operations | ⏭️ | — | Tested via real deployments only |
| SSH Connections | ⏭️ | — | Requires real infrastructure |

## Adding New Tests

### Test a New Config Loader

```python
def test_new_service_config_loads(self, tmp_tenant_dir):
    """Should load NEW_SERVICE config."""
    (tmp_tenant_dir / "vars" / "all.py").write_text("""
NEW_SERVICE = {
    "host.local": {"setting": "value"}
}
""")
    config = load_service_config(tmp_tenant_dir, "NEW_SERVICE")
    assert config["host.local"]["setting"] == "value"
```

### Test a New Task

```python
def test_new_task_registered(self):
    """NEW_TASK should be registered."""
    assert "new_task" in TASK_REGISTRY
    assert len(TASK_REGISTRY["new_task"]) > 0
    entry = TASK_REGISTRY["new_task"][0]
    assert entry.config_attr == "NEW_SERVICE"
    assert entry.op_type == "standard"
```

### Test 3-Tier Inheritance

```python
def test_new_service_inheritance(self, tmp_tenant_dir):
    """Should correctly inherit NEW_SERVICE config."""
    (tmp_tenant_dir / "vars" / "all.py").write_text("""
NEW_SERVICE = {"host.location": {"from": "all"}}
""")
    (tmp_tenant_dir / "vars" / "location" / "location.py").write_text("""
NEW_SERVICE = {"host.location": {"from": "location"}}
""")
    config = load_service_config(tmp_tenant_dir, "NEW_SERVICE")
    assert config["host.location"]["from"] == "location"  # Location wins
```

## CI/CD Integration

For continuous integration, use:

```bash
# Exit with error if tests fail
python3 -m pytest tests/ -v --tb=short
echo $?  # Check exit code (0 = success)
```

## Performance

Tests run in ~2 seconds (146 tests):
- Unit tests: ~1.5 seconds
- Integration tests: ~0.5 seconds
- No external dependencies (no network, SSH, or real hosts)

## Troubleshooting

### Import Errors
Ensure `PYTHONPATH` includes framework root:
```bash
cd ~/src/floads/flamelet
python3 -m pytest tests/
```

### Assertion Failures
Use verbose mode with long tracebacks:
```bash
python3 -m pytest tests/ -v --tb=long
```

### Specific Test Failures
Run single test to debug:
```bash
python3 -m pytest tests/unit/test_loaders.py::TestLoadServiceConfig::test_inheritance_hierarchy_all_to_host -v
```

### Mock Host Errors
Ensure fixtures in `conftest.py` are using correct pyinfra API:
```python
Inventory(
    (hosts_list, global_config),
    group_name=(group_hosts, group_config),
)
```

## Best Practices

1. **Use fixtures**: Don't create inline mocks — use `tmp_tenant_dir`, `mock_inventory`, etc.
2. **Test behavior, not implementation**: Test what configs get loaded, not how they're loaded
3. **Test inheritance**: Always verify 3-tier merging for new service configs
4. **Keep tests isolated**: Each test should be independent
5. **Use clear assertions**: `assert x in y` is better than `assert y` with x hidden inside

## Related Documentation

- **[CLAUDE.md](CLAUDE.md)** — Framework reference for AI
- **[README.md](README.md)** — Architecture and quick start
- **[core/tasks/__init__.py](core/tasks/__init__.py)** — TASK_REGISTRY source
- **[core/tasks/loader.py](core/tasks/loader.py)** — Config loader source
