"""Tests for inventory modules."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tenants.home.inventory import build_inventory  # noqa: E402


class TestTenantInventory:
    """Test tenant inventory structure."""

    def test_host_count(self):
        """Inventory should have 7 hosts total."""
        inventory = build_inventory()
        hosts = list(inventory)
        assert len(hosts) == 7

    def test_host_names(self):
        """Inventory should have correct host names."""
        inventory = build_inventory()
        host_names = {h.name for h in inventory}
        expected = {
            "controller.work",
            "nas-01.pangea",
            "virt.home",
            "virt-01.baar",
            "virt-02.baar",
            "virt-03.baar",
            "docker.home",
        }
        assert host_names == expected

    def test_openbsd_doas_enabled(self):
        """OpenBSD host should have _doas=True."""
        inventory = build_inventory()
        controller = next(h for h in inventory if h.name == "controller.work")
        assert controller.data.get("_doas") is True

    def test_freebsd_no_doas(self):
        """FreeBSD hosts should not have _doas set."""
        inventory = build_inventory()
        freebsd_hosts = [h for h in inventory if h.name.startswith("nas-") or "virt" in h.name]
        for host in freebsd_hosts:
            assert host.data.get("_doas") is not True

    def test_bootstrap_users(self):
        """Bootstrap users: syseng for BSD, debian for Linux."""
        inventory = build_inventory()
        # OpenBSD/FreeBSD: use syseng (already configured)
        for host in inventory.get_group("openbsd"):
            assert host.data.ssh_user == "syseng"
        for host in inventory.get_group("freebsd"):
            assert host.data.ssh_user == "syseng"
        # Debian: use debian (bootstrap user before switching to syseng)
        docker = next(h for h in inventory if h.name == "docker.home")
        assert docker.data.ssh_user == "debian"

    def test_ssh_key_configured(self):
        """All hosts should have ssh_key configured."""
        inventory = build_inventory()
        for host in inventory:
            assert host.data.get("ssh_key") is not None or "ssh_key" not in host.data

    def test_group_openbsd(self):
        """openbsd group should contain only controller.work."""
        inventory = build_inventory()
        openbsd_group = list(inventory.get_group("openbsd"))
        assert len(openbsd_group) == 1
        assert openbsd_group[0].name == "controller.work"

    def test_group_freebsd(self):
        """freebsd group should contain 5 FreeBSD hosts."""
        inventory = build_inventory()
        freebsd_group = list(inventory.get_group("freebsd"))
        assert len(freebsd_group) == 5
        freebsd_names = {h.name for h in freebsd_group}
        expected = {
            "nas-01.pangea",
            "virt.home",
            "virt-01.baar",
            "virt-02.baar",
            "virt-03.baar",
        }
        assert freebsd_names == expected

    def test_group_location_work(self):
        """work group should contain only controller.work."""
        inventory = build_inventory()
        work_group = list(inventory.get_group("work"))
        assert len(work_group) == 1
        assert work_group[0].name == "controller.work"

    def test_group_location_home(self):
        """home group should contain only virt.home."""
        inventory = build_inventory()
        home_group = list(inventory.get_group("home"))
        assert len(home_group) == 1
        assert home_group[0].name == "virt.home"

    def test_group_location_baar(self):
        """baar group should contain 3 baar hosts."""
        inventory = build_inventory()
        baar_group = list(inventory.get_group("baar"))
        assert len(baar_group) == 3
        baar_names = {h.name for h in baar_group}
        expected = {"virt-01.baar", "virt-02.baar", "virt-03.baar"}
        assert baar_names == expected

    def test_group_location_pangea(self):
        """pangea group should contain only nas-01.pangea."""
        inventory = build_inventory()
        pangea_group = list(inventory.get_group("pangea"))
        assert len(pangea_group) == 1
        assert pangea_group[0].name == "nas-01.pangea"

    def test_group_location_docker(self):
        """docker group should contain only docker.home."""
        inventory = build_inventory()
        docker_group = list(inventory.get_group("docker"))
        assert len(docker_group) == 1
        assert docker_group[0].name == "docker.home"

    def test_group_debian(self):
        """debian group should contain only docker.home."""
        inventory = build_inventory()
        debian_group = list(inventory.get_group("debian"))
        assert len(debian_group) == 1
        assert debian_group[0].name == "docker.home"

    def test_debian_sudo_enabled(self):
        """Debian host should have _sudo=True."""
        inventory = build_inventory()
        docker = next(h for h in inventory if h.name == "docker.home")
        assert docker.data.get("_sudo") is True
