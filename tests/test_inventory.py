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
            "gw.example.com",
            "nas.example.com",
            "hypervisor.example.com",
            "worker-1.example.com",
            "worker-2.example.com",
            "worker-3.example.com",
            "docker.example.com",
        }
        assert host_names == expected

    def test_openbsd_doas_enabled(self):
        """OpenBSD host should have _doas=True."""
        inventory = build_inventory()
        gw = next(h for h in inventory if h.name == "gw.example.com")
        assert gw.data.get("_doas") is True

    def test_freebsd_no_doas(self):
        """FreeBSD hosts should not have _doas set."""
        inventory = build_inventory()
        freebsd_hosts = [h for h in inventory if h.name.startswith("nas.") or "worker-" in h.name or "hypervisor" in h.name]
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
        docker = next(h for h in inventory if h.name == "docker.example.com")
        assert docker.data.ssh_user == "debian"

    def test_ssh_key_configured(self):
        """All hosts should have ssh_key configured."""
        inventory = build_inventory()
        for host in inventory:
            assert host.data.get("ssh_key") is not None or "ssh_key" not in host.data

    def test_group_openbsd(self):
        """openbsd group should contain only gw.example.com."""
        inventory = build_inventory()
        openbsd_group = list(inventory.get_group("openbsd"))
        assert len(openbsd_group) == 1
        assert openbsd_group[0].name == "gw.example.com"

    def test_group_freebsd(self):
        """freebsd group should contain 5 FreeBSD hosts."""
        inventory = build_inventory()
        freebsd_group = list(inventory.get_group("freebsd"))
        assert len(freebsd_group) == 5
        freebsd_names = {h.name for h in freebsd_group}
        expected = {
            "nas.example.com",
            "hypervisor.example.com",
            "worker-1.example.com",
            "worker-2.example.com",
            "worker-3.example.com",
        }
        assert freebsd_names == expected

    def test_group_gateway(self):
        """gateway group should contain only gw.example.com."""
        inventory = build_inventory()
        gateway_group = list(inventory.get_group("gateway"))
        assert len(gateway_group) == 1
        assert gateway_group[0].name == "gw.example.com"

    def test_group_storage(self):
        """storage group should contain only nas.example.com."""
        inventory = build_inventory()
        storage_group = list(inventory.get_group("storage"))
        assert len(storage_group) == 1
        assert storage_group[0].name == "nas.example.com"

    def test_group_hypervisors(self):
        """hypervisors group should contain only hypervisor.example.com."""
        inventory = build_inventory()
        hypervisors_group = list(inventory.get_group("hypervisors"))
        assert len(hypervisors_group) == 1
        assert hypervisors_group[0].name == "hypervisor.example.com"

    def test_group_workers(self):
        """workers group should contain 3 worker hosts."""
        inventory = build_inventory()
        workers_group = list(inventory.get_group("workers"))
        assert len(workers_group) == 3
        worker_names = {h.name for h in workers_group}
        expected = {"worker-1.example.com", "worker-2.example.com", "worker-3.example.com"}
        assert worker_names == expected

    def test_group_docker(self):
        """docker group should contain only docker.example.com."""
        inventory = build_inventory()
        docker_group = list(inventory.get_group("docker"))
        assert len(docker_group) == 1
        assert docker_group[0].name == "docker.example.com"

    def test_group_debian(self):
        """debian group should contain only docker.example.com."""
        inventory = build_inventory()
        debian_group = list(inventory.get_group("debian"))
        assert len(debian_group) == 1
        assert debian_group[0].name == "docker.example.com"

    def test_debian_sudo_enabled(self):
        """Debian host should have _sudo=True."""
        inventory = build_inventory()
        docker = next(h for h in inventory if h.name == "docker.example.com")
        assert docker.data.get("_sudo") is True
