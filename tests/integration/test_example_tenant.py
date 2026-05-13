"""Integration tests using the example home tenant."""

from pathlib import Path

from core.cli import build_add_ops_func, load_tenant_inventory, load_tenant_vars_module
from core.tasks import TASK_REGISTRY
from core.tasks.loader import load_packages_config, load_service_config

# Example tenant on disk in the framework repo
EXAMPLE_TENANT = Path(__file__).parent.parent.parent / "tenants" / "flamelet-example"


class TestExampleTenant:
    """Test the example home tenant (full end-to-end config loading)."""

    def test_example_inventory_loads(self):
        """Example tenant inventory should load 8 hosts."""
        inventory = load_tenant_inventory(EXAMPLE_TENANT)
        hosts = list(inventory)
        assert len(hosts) == 8
        host_names = {h.name for h in hosts}
        assert "gw.example.com" in host_names
        assert "docker.example.com" in host_names

    def test_example_vars_module_loads(self):
        """Example tenant vars module should load with USERS and GROUPS."""
        vars_module = load_tenant_vars_module(EXAMPLE_TENANT)
        assert hasattr(vars_module, "USERS")
        assert hasattr(vars_module, "GROUPS")
        assert "syseng" in vars_module.USERS
        assert "keep" in vars_module.USERS

    def test_example_monit_config_loads(self):
        """Example tenant should load MONIT config (from location override)."""
        config = load_service_config(EXAMPLE_TENANT, "MONIT")
        assert isinstance(config, dict)
        # MONIT is defined in location/example.py
        assert "gw.example.com" in config
        assert config["gw.example.com"]["daemon"] == 120

    def test_example_wireguard_config_loads(self):
        """Example tenant should load WIREGUARD config (from location override)."""
        config = load_service_config(EXAMPLE_TENANT, "WIREGUARD")
        assert isinstance(config, dict)
        assert "gw.example.com" in config
        assert "wg0" in config["gw.example.com"]["interfaces"]

    def test_example_packages_config_linux(self):
        """Example tenant should load PACKAGES config for Linux."""
        config = load_packages_config(EXAMPLE_TENANT, "docker.example.com", "Linux")
        assert isinstance(config, dict)
        # Global PACKAGES from all.py + host override from hosts/docker_example_com.py
        assert "curl" in config.get("Linux", [])
        assert "docker-ce" in config.get("Linux", [])

    def test_example_packages_config_freebsd(self):
        """Example tenant should load PACKAGES config for FreeBSD."""
        config = load_packages_config(EXAMPLE_TENANT, "nas.example.com", "FreeBSD")
        assert isinstance(config, dict)
        # From global all.py (no host override for nas)
        assert "curl" in config.get("FreeBSD", [])
        assert "htop" in config.get("FreeBSD", [])

    def test_example_add_ops_function_builds(self):
        """Example tenant should build a valid add_ops function."""
        vars_module = load_tenant_vars_module(EXAMPLE_TENANT)
        add_ops = build_add_ops_func(EXAMPLE_TENANT, vars_module)
        assert callable(add_ops)
        # Signature should be (state, inventory, target_hosts=None, task="all")
        assert "state" in add_ops.__code__.co_varnames
        assert "inventory" in add_ops.__code__.co_varnames
        assert "task" in add_ops.__code__.co_varnames

    def test_config_inheritance_example(self):
        """3-tier inheritance should work: all.py < location/example.py < hosts/"""
        # Load MONIT twice: from all.py it's empty, from location/example.py it has gw config
        config = load_service_config(EXAMPLE_TENANT, "MONIT")
        assert "gw.example.com" in config  # Comes from location/example.py
        # Other hosts have empty MONIT from all.py
        assert config.get("nas.example.com", {}) == {}

    def test_all_service_configs_loadable(self):
        """Every service in all.py should load without error."""
        service_names = [
            "MONIT",
            "WIREGUARD",
            "DOCKER",
            "SERVICES",
            "SYSCTL",
            "POSTGRESQL",
            "NGINX",
        ]
        for service_name in service_names:
            config = load_service_config(EXAMPLE_TENANT, service_name)
            assert isinstance(config, dict)

    def test_all_task_configs_loadable_from_task_registry(self):
        """Every config_attr in TASK_REGISTRY should load from example tenant."""
        for task_name, entries in TASK_REGISTRY.items():
            for entry in entries:
                if entry.config_attr and entry.config_attr != "PACKAGES":
                    # Load service config (skip PACKAGES, it's OS-keyed)
                    config = load_service_config(EXAMPLE_TENANT, entry.config_attr)
                    assert isinstance(config, dict), f"Failed to load {entry.config_attr}"
