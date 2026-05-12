"""Tests for config loaders (3-tier inheritance)."""

from core.tasks.loader import load_service_config, load_packages_config


class TestLoadServiceConfig:
    """Test 3-tier config inheritance for service configs."""

    def test_load_from_all_py(self, tmp_tenant_dir):
        """Should load configs from vars/all.py."""
        # Create a config in all.py
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
MONIT = {
    "test.local": {"daemon": 120},
}
""")
        config = load_service_config(tmp_tenant_dir, "MONIT")
        assert "test.local" in config
        assert config["test.local"]["daemon"] == 120

    def test_load_from_location_py(self, tmp_tenant_dir):
        """Should load and merge configs from vars/location/*.py."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
MONIT = {
    "test.example.local": {"daemon": 120},
}
""")
        (tmp_tenant_dir / "vars" / "location" / "local.py").write_text("""
MONIT = {
    "test.example.local": {"mmonit_url": "http://monit:pass@10.0.0.1:8081"},
}
""")
        config = load_service_config(tmp_tenant_dir, "MONIT")
        assert config["test.example.local"]["daemon"] == 120
        assert config["test.example.local"]["mmonit_url"] == "http://monit:pass@10.0.0.1:8081"

    def test_load_from_hosts_py(self, tmp_tenant_dir):
        """Should load and merge configs from vars/hosts/*.py."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
MONIT = {
    "web.example.com": {"daemon": 120},
}
""")
        (tmp_tenant_dir / "vars" / "hosts" / "web_example_com.py").write_text("""
MONIT = {
    "web.example.com": {"httpd_port": 2812},
}
""")
        config = load_service_config(tmp_tenant_dir, "MONIT")
        assert config["web.example.com"]["daemon"] == 120
        assert config["web.example.com"]["httpd_port"] == 2812

    def test_inheritance_hierarchy_all_to_host(self, tmp_tenant_dir):
        """Should correctly merge all.py < location/*.py < hosts/*.py."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
WIREGUARD = {
    "vpn.home": {"port": 51820, "address": "10.0.0.1/24"},
}
""")
        (tmp_tenant_dir / "vars" / "location" / "home.py").write_text("""
WIREGUARD = {
    "vpn.home": {"private_key": "location_key"},
}
""")
        (tmp_tenant_dir / "vars" / "hosts" / "vpn_home.py").write_text("""
WIREGUARD = {
    "vpn.home": {"private_key": "host_key", "keepalive": 25},
}
""")
        config = load_service_config(tmp_tenant_dir, "WIREGUARD")
        host_config = config["vpn.home"]

        # All-level values
        assert host_config["port"] == 51820
        assert host_config["address"] == "10.0.0.1/24"

        # Location-level default
        assert host_config["private_key"] == "host_key"  # Host override wins

        # Host-level additions
        assert host_config["keepalive"] == 25

    def test_empty_config_attr(self, tmp_tenant_dir):
        """Should return empty dict if attribute not found."""
        config = load_service_config(tmp_tenant_dir, "NONEXISTENT_SERVICE")
        assert config == {}

    def test_missing_location_file_ok(self, tmp_tenant_dir):
        """Should not fail if location/*.py file is missing."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
MONIT = {"test.local": {"daemon": 120}}
""")
        # No location file — should still work
        config = load_service_config(tmp_tenant_dir, "MONIT")
        assert "test.local" in config

    def test_missing_hosts_file_ok(self, tmp_tenant_dir):
        """Should not fail if hosts/*.py file is missing."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
MONIT = {"test.local": {"daemon": 120}}
""")
        # No hosts file — should still work
        config = load_service_config(tmp_tenant_dir, "MONIT")
        assert "test.local" in config


class TestLoadPackagesConfig:
    """Test OS-keyed package list loading."""

    def test_load_packages_from_all_py(self, tmp_tenant_dir):
        """Should load packages from vars/all.py."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl", "git"],
    "FreeBSD": ["curl"],
}
""")
        config = load_packages_config(tmp_tenant_dir, "test.local", "Linux")
        assert "curl" in config["Linux"]
        assert "git" in config["Linux"]

    def test_load_packages_per_os(self, tmp_tenant_dir):
        """Should return OS-keyed package list."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl", "git", "htop"],
    "FreeBSD": ["curl", "git"],
    "OpenBSD": ["curl"],
}
""")
        linux_config = load_packages_config(tmp_tenant_dir, "test.local", "Linux")
        freebsd_config = load_packages_config(tmp_tenant_dir, "test.local", "FreeBSD")

        assert len(linux_config["Linux"]) >= 3
        assert len(freebsd_config["FreeBSD"]) >= 2

    def test_load_packages_with_host_override(self, tmp_tenant_dir):
        """Should merge all.py and hosts/*.py packages."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl", "git"],
}
""")
        (tmp_tenant_dir / "vars" / "hosts" / "test_local.py").write_text("""
PACKAGES = {
    "Linux": ["htop"],
}
""")
        config = load_packages_config(tmp_tenant_dir, "test.local", "Linux")

        # Should have packages from both all.py and hosts/*.py
        assert "curl" in config["Linux"]
        assert "git" in config["Linux"]
        assert "htop" in config["Linux"]

        # Should deduplicate
        assert len(set(config["Linux"])) == len(config["Linux"])

    def test_packages_deduplication(self, tmp_tenant_dir):
        """Should remove duplicate packages."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl", "git", "curl"],
}
""")
        config = load_packages_config(tmp_tenant_dir, "test.local", "Linux")

        # Duplicates should be removed
        assert config["Linux"].count("curl") == 1

    def test_missing_os_key(self, tmp_tenant_dir):
        """Should return empty package list for missing OS."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {
    "Linux": ["curl"],
}
""")
        config = load_packages_config(tmp_tenant_dir, "test.local", "NonExistentOS")
        assert config == {"NonExistentOS": []}

    def test_location_extraction_from_hostname(self, tmp_tenant_dir):
        """Should extract location from hostname (last dot segment)."""
        (tmp_tenant_dir / "vars" / "all.py").write_text("""
PACKAGES = {"Linux": ["base"]}
""")
        (tmp_tenant_dir / "vars" / "location" / "home.py").write_text("""
PACKAGES = {
    "Linux": ["home-pkg"],
}
""")
        # Hostname: app.home → location: home (last dot segment)
        config = load_packages_config(tmp_tenant_dir, "app.home", "Linux")
        assert "home-pkg" in config["Linux"]
        assert "base" in config["Linux"]
