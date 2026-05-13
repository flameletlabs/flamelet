"""Integration tests for config loading during deployment."""

from core.cli import build_add_ops_func, load_tenant_inventory, load_tenant_vars_module
from core.tasks.loader import load_packages_config, load_service_config


class TestDeploymentConfigLoading:
    """Test that configs load correctly for deployment."""

    def test_monit_config_loads(self, tmp_tenant_dir):
        """Should load MONIT config for deployment."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
MONIT = {
    "test.local": {
        "daemon": 120,
        "checks": {"system": "check system test.local"},
    }
}
""")
        config = load_service_config(tmp_tenant_dir, "MONIT")
        assert "test.local" in config
        assert config["test.local"]["daemon"] == 120

    def test_packages_config_loads(self, tmp_tenant_dir):
        """Should load PACKAGES config for deployment."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl", "git"],
    "FreeBSD": ["curl"],
}
""")
        linux_config = load_packages_config(tmp_tenant_dir, "test.local", "Linux")
        freebsd_config = load_packages_config(tmp_tenant_dir, "test.local", "FreeBSD")

        assert "curl" in linux_config["Linux"]
        assert "curl" in freebsd_config["FreeBSD"]

    def test_inventory_loads(self, tmp_tenant_dir):
        """Should load inventory for deployment."""
        inventory = load_tenant_inventory(tmp_tenant_dir)
        assert inventory is not None
        hosts = list(inventory)
        assert len(hosts) > 0

    def test_vars_module_loads(self, tmp_tenant_dir):
        """Should load vars module for deployment."""
        vars_module = load_tenant_vars_module(tmp_tenant_dir)
        assert hasattr(vars_module, "USERS")
        assert hasattr(vars_module, "GROUPS")

    def test_add_ops_func_builds(self, tmp_tenant_dir):
        """Should build add_ops function for deployment."""
        vars_module = load_tenant_vars_module(tmp_tenant_dir)
        add_ops = build_add_ops_func(tmp_tenant_dir, vars_module)
        assert callable(add_ops)

    def test_config_inheritance_during_loading(self, tmp_tenant_dir):
        """Should correctly apply 3-tier inheritance when loading configs."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
WIREGUARD = {
    "vpn.home": {"port": 51820},
}
""")

        (tmp_tenant_dir / "vars" / "location" / "home.py").write_text("""
WIREGUARD = {
    "vpn.home": {"address": "10.0.0.1/24"},
}
""")

        config = load_service_config(tmp_tenant_dir, "WIREGUARD")
        assert config["vpn.home"]["port"] == 51820
        assert config["vpn.home"]["address"] == "10.0.0.1/24"
