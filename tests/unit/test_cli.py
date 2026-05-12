"""Tests for CLI argument parsing and tenant discovery."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from core.cli import (
    load_tenant_inventory,
    load_tenant_vars_module,
    build_add_ops_func,
)


class TestLoadTenantInventory:
    """Test inventory.py loading."""

    def test_load_valid_inventory(self, tmp_tenant_dir):
        """Should load inventory from valid inventory.py."""
        inventory = load_tenant_inventory(tmp_tenant_dir)
        assert inventory is not None
        # Inventory should have hosts
        hosts = list(inventory)
        assert len(hosts) > 0

    def test_missing_inventory_raises_error(self, tmp_tenant_dir):
        """Should raise error if inventory.py is missing."""
        inventory_file = tmp_tenant_dir / "inventory.py"
        inventory_file.unlink()

        with pytest.raises(RuntimeError, match="inventory.py not found"):
            load_tenant_inventory(tmp_tenant_dir)

    def test_inventory_missing_build_inventory_raises_error(self, tmp_tenant_dir):
        """Should raise error if inventory.py doesn't define build_inventory()."""
        (tmp_tenant_dir / "inventory.py").write_text("# Invalid inventory")

        with pytest.raises(RuntimeError, match="build_inventory"):
            load_tenant_inventory(tmp_tenant_dir)


class TestLoadTenantVarsModule:
    """Test vars/__init__.py loading."""

    def test_load_valid_vars_module(self, tmp_tenant_dir):
        """Should load vars module."""
        vars_module = load_tenant_vars_module(tmp_tenant_dir)
        assert vars_module is not None
        assert hasattr(vars_module, "USERS")
        assert hasattr(vars_module, "GROUPS")

    def test_missing_vars_raises_error(self, tmp_tenant_dir):
        """Should raise error if vars/__init__.py is missing."""
        vars_file = tmp_tenant_dir / "vars" / "__init__.py"
        vars_file.unlink()

        with pytest.raises(RuntimeError, match="vars/__init__.py not found"):
            load_tenant_vars_module(tmp_tenant_dir)


class TestBuildAddOpsFunc:
    """Test add_ops function building."""

    def test_add_ops_func_callable(self, tmp_tenant_dir):
        """Should return a callable add_ops function."""
        vars_module = load_tenant_vars_module(tmp_tenant_dir)
        add_ops = build_add_ops_func(tmp_tenant_dir, vars_module)

        assert callable(add_ops)

    def test_add_ops_func_has_correct_signature(self, tmp_tenant_dir):
        """add_ops function should accept expected parameters."""
        vars_module = load_tenant_vars_module(tmp_tenant_dir)
        add_ops = build_add_ops_func(tmp_tenant_dir, vars_module)

        # Check that it's callable with the expected parameters
        import inspect
        sig = inspect.signature(add_ops)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "inventory" in params
        assert "target_hosts" in params
        assert "task" in params

    def test_add_ops_handles_unknown_task_gracefully(
        self, tmp_tenant_dir, mock_inventory, mock_state
    ):
        """Should handle unknown tasks gracefully (with warning, not error)."""
        vars_module = load_tenant_vars_module(tmp_tenant_dir)
        add_ops = build_add_ops_func(tmp_tenant_dir, vars_module)

        # Should not raise error even for unknown task
        # (won't actually queue ops, just skips the task)
        add_ops(mock_state, mock_inventory, target_hosts=None, task="nonexistent_task")
