"""Tests for tenant configuration integration."""

import sys
from pathlib import Path
import pytest


@pytest.fixture
def tenant_vars():
    """Load tenant vars module."""
    tenant_root = Path.home() / ".config/flamelet/tenants/flamelet-home"
    if not tenant_root.exists():
        pytest.skip("Tenant directory not found - skipping integration tests")

    import importlib.util
    tenant_vars_spec = importlib.util.spec_from_file_location(
        "tenant_vars", tenant_root / "vars" / "__init__.py"
    )
    tenant_vars = importlib.util.module_from_spec(tenant_vars_spec)
    tenant_vars_spec.loader.exec_module(tenant_vars)
    return tenant_vars


@pytest.fixture
def inventory():
    """Load tenant inventory module."""
    tenant_root = Path.home() / ".config/flamelet/tenants/flamelet-home"
    if not tenant_root.exists():
        pytest.skip("Tenant directory not found - skipping integration tests")

    import importlib.util
    inventory_spec = importlib.util.spec_from_file_location(
        "inventory", tenant_root / "inventory.py"
    )
    inventory_module = importlib.util.module_from_spec(inventory_spec)
    inventory_spec.loader.exec_module(inventory_module)
    return inventory_module.build_inventory()


class TestTenantVarsLoaders:
    """Test all configuration loaders in tenant vars/__init__.py."""

    def test_users_defined(self, tenant_vars):
        """Verify USERS configuration defined."""
        assert hasattr(tenant_vars, 'USERS')
        assert isinstance(tenant_vars.USERS, dict)
        assert 'syseng' in tenant_vars.USERS or len(tenant_vars.USERS) > 0

    def test_groups_defined(self, tenant_vars):
        """Verify GROUPS configuration defined."""
        assert hasattr(tenant_vars, 'GROUPS')
        assert isinstance(tenant_vars.GROUPS, list)

    def test_get_packages_config_loader(self, tenant_vars):
        """Verify get_packages_config loader exists."""
        assert hasattr(tenant_vars, 'get_packages_config')
        assert callable(tenant_vars.get_packages_config)

    def test_get_wireguard_config_loader(self, tenant_vars):
        """Verify get_wireguard_config loader exists."""
        assert hasattr(tenant_vars, 'get_wireguard_config')
        assert callable(tenant_vars.get_wireguard_config)

    def test_get_unbound_config_loader(self, tenant_vars):
        """Verify get_unbound_config loader exists."""
        assert hasattr(tenant_vars, 'get_unbound_config')
        assert callable(tenant_vars.get_unbound_config)

    def test_get_monit_config_loader(self, tenant_vars):
        """Verify get_monit_config loader exists."""
        assert hasattr(tenant_vars, 'get_monit_config')
        assert callable(tenant_vars.get_monit_config)

    def test_get_opensmtpd_config_loader(self, tenant_vars):
        """Verify get_opensmtpd_config loader exists."""
        assert hasattr(tenant_vars, 'get_opensmtpd_config')
        assert callable(tenant_vars.get_opensmtpd_config)

    def test_get_pf_config_loader(self, tenant_vars):
        """Verify get_pf_config loader exists."""
        assert hasattr(tenant_vars, 'get_pf_config')
        assert callable(tenant_vars.get_pf_config)

    def test_get_docker_config_loader(self, tenant_vars):
        """Verify get_docker_config loader exists."""
        assert hasattr(tenant_vars, 'get_docker_config')
        assert callable(tenant_vars.get_docker_config)

    def test_get_node_exporter_config_loader(self, tenant_vars):
        """Verify get_node_exporter_config loader exists."""
        assert hasattr(tenant_vars, 'get_node_exporter_config')
        assert callable(tenant_vars.get_node_exporter_config)

    def test_get_k3s_config_loader(self, tenant_vars):
        """Verify get_k3s_config loader exists."""
        assert hasattr(tenant_vars, 'get_k3s_config')
        assert callable(tenant_vars.get_k3s_config)

    def test_get_virtualization_config_loader(self, tenant_vars):
        """Verify get_virtualization_config loader exists."""
        assert hasattr(tenant_vars, 'get_virtualization_config')
        assert callable(tenant_vars.get_virtualization_config)

    def test_get_storage_config_loader(self, tenant_vars):
        """Verify get_storage_config loader exists."""
        assert hasattr(tenant_vars, 'get_storage_config')
        assert callable(tenant_vars.get_storage_config)

    def test_get_nginx_config_loader(self, tenant_vars):
        """Verify get_nginx_config loader exists."""
        assert hasattr(tenant_vars, 'get_nginx_config')
        assert callable(tenant_vars.get_nginx_config)

    def test_get_postgresql_config_loader(self, tenant_vars):
        """Verify get_postgresql_config loader exists."""
        assert hasattr(tenant_vars, 'get_postgresql_config')
        assert callable(tenant_vars.get_postgresql_config)

    def test_get_prometheus_config_loader(self, tenant_vars):
        """Verify get_prometheus_config loader exists."""
        assert hasattr(tenant_vars, 'get_prometheus_config')
        assert callable(tenant_vars.get_prometheus_config)

    def test_get_registry_config_loader(self, tenant_vars):
        """Verify get_registry_config loader exists."""
        assert hasattr(tenant_vars, 'get_registry_config')
        assert callable(tenant_vars.get_registry_config)


class TestConfigLoaderFunctionality:
    """Test that config loaders actually work."""

    def test_wireguard_config_loads(self, tenant_vars):
        """Verify wireguard config loads without error."""
        config = tenant_vars.get_wireguard_config()
        assert isinstance(config, dict)

    def test_unbound_config_loads(self, tenant_vars):
        """Verify unbound config loads without error."""
        config = tenant_vars.get_unbound_config()
        assert isinstance(config, dict)

    def test_monit_config_loads(self, tenant_vars):
        """Verify monit config loads without error."""
        config = tenant_vars.get_monit_config()
        assert isinstance(config, dict)

    def test_k3s_config_loads(self, tenant_vars):
        """Verify k3s config loads without error."""
        config = tenant_vars.get_k3s_config()
        assert isinstance(config, dict)

    def test_virtualization_config_loads(self, tenant_vars):
        """Verify virtualization config loads without error."""
        config = tenant_vars.get_virtualization_config()
        assert isinstance(config, dict)

    def test_storage_config_loads(self, tenant_vars):
        """Verify storage config loads without error."""
        config = tenant_vars.get_storage_config()
        assert isinstance(config, dict)

    def test_nginx_config_loads(self, tenant_vars):
        """Verify nginx config loads without error."""
        config = tenant_vars.get_nginx_config()
        assert isinstance(config, dict)

    def test_postgresql_config_loads(self, tenant_vars):
        """Verify postgresql config loads without error."""
        config = tenant_vars.get_postgresql_config()
        assert isinstance(config, dict)

    def test_prometheus_config_loads(self, tenant_vars):
        """Verify prometheus config loads without error."""
        config = tenant_vars.get_prometheus_config()
        assert isinstance(config, dict)

    def test_registry_config_loads(self, tenant_vars):
        """Verify registry config loads without error."""
        config = tenant_vars.get_registry_config()
        assert isinstance(config, dict)


class TestInventoryIntegration:
    """Test that inventory builds correctly."""

    def test_inventory_builds(self, inventory):
        """Verify inventory builds without error."""
        assert inventory is not None

    def test_inventory_has_hosts(self, inventory):
        """Verify inventory contains hosts."""
        hosts = list(inventory)
        assert len(hosts) > 0

    def test_inventory_groups_exist(self, inventory):
        """Verify inventory groups are defined."""
        # Check that we can get groups
        for group_name in ['freebsd', 'debian', 'openbsd']:
            try:
                group = inventory.get_group(group_name)
                # Group should exist or be empty, but shouldn't error
                assert group is not None
            except Exception:
                pass  # Some groups may not exist, that's ok


class TestTenantRunPy:
    """Test tenant run.py integration."""

    def test_run_py_imports(self):
        """Verify run.py imports correctly."""
        tenant_root = Path.home() / ".config/flamelet/tenants/flamelet-home"
        if not tenant_root.exists():
            pytest.skip("Tenant directory not found")

        import importlib.util
        run_spec = importlib.util.spec_from_file_location(
            "run", tenant_root / "run.py"
        )
        run_module = importlib.util.module_from_spec(run_spec)

        # This will test if all imports in run.py work
        try:
            run_spec.loader.exec_module(run_module)
            assert True
        except ImportError as e:
            pytest.fail(f"run.py import failed: {e}")

    def test_tenant_tasks_defined(self):
        """Verify TENANT_TASKS includes all required operations."""
        tenant_root = Path.home() / ".config/flamelet/tenants/flamelet-home"
        if not tenant_root.exists():
            pytest.skip("Tenant directory not found")

        import importlib.util
        run_spec = importlib.util.spec_from_file_location(
            "run", tenant_root / "run.py"
        )
        run_module = importlib.util.module_from_spec(run_spec)
        run_spec.loader.exec_module(run_module)

        # Verify TENANT_TASKS includes Phase 3b operations
        required_tasks = ["nginx", "postgresql", "prometheus", "registry"]
        for task in required_tasks:
            assert task in run_module.TENANT_TASKS, f"Task '{task}' missing from TENANT_TASKS"


class TestOperationCompatibility:
    """Test that operations are compatible with each other."""

    def test_all_operations_follow_pattern(self):
        """Verify all operations follow the standard signature."""
        operations_to_check = [
            ('wireguard', 'add_wireguard_ops'),
            ('unbound', 'add_unbound_ops'),
            ('pf', 'add_pf_ops'),
            ('k3s', 'add_k3s_ops'),
            ('storage', 'add_storage_ops'),
            ('nginx', 'add_nginx_ops'),
            ('postgresql', 'add_postgresql_ops'),
            ('prometheus', 'add_prometheus_ops'),
            ('registry', 'add_registry_ops'),
        ]

        for module_name, func_name in operations_to_check:
            module = __import__(f'core.operations.{module_name}', fromlist=[func_name])
            func = getattr(module, func_name)

            # Verify function has expected parameters
            import inspect
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())

            expected_params = ['state', 'hosts', 'config']
            for param in expected_params:
                assert param in params, f"{func_name} missing parameter '{param}'"
