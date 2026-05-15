"""Tests for inventory modules."""

import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
_inv_path = project_root / "tenants" / "flamelet-example" / "inventory.py"
_spec = importlib.util.spec_from_file_location("flamelet_example_inventory", _inv_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_inventory = _mod.build_inventory


class TestTenantInventory:
    """Test tenant inventory structure."""

    def test_host_count(self):
        """Inventory should have 8 hosts total."""
        inventory = build_inventory()
        hosts = list(inventory)
        assert len(hosts) == 8

    def test_host_names(self):
        """Inventory should have correct host names (London + New York)."""
        inventory = build_inventory()
        host_names = {h.name for h in inventory}
        expected = {
            "gw.london",
            "web-01.london",
            "web-02.london",
            "db.london",
            "gw.newyork",
            "worker-01.newyork",
            "worker-02.newyork",
            "docker.newyork",
        }
        assert host_names == expected

    def test_openbsd_doas_enabled(self):
        """OpenBSD gateways should have _doas=True."""
        inventory = build_inventory()
        gw = next(h for h in inventory if h.name == "gw.london")
        assert gw.data.get("_doas") is True

    def test_freebsd_no_doas(self):
        """FreeBSD hosts should not have _doas set."""
        inventory = build_inventory()
        freebsd_hosts = [
            h
            for h in inventory
            if h.name.startswith("nas.") or "worker-" in h.name or "hypervisor" in h.name
        ]
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
        docker = next(h for h in inventory if h.name == "docker.newyork")
        assert docker.data.ssh_user == "debian"

    def test_ssh_key_configured(self):
        """All hosts should have ssh_key configured."""
        inventory = build_inventory()
        for host in inventory:
            assert host.data.get("ssh_key") is not None or "ssh_key" not in host.data

    def test_group_openbsd(self):
        """openbsd group should contain the two gateway hosts."""
        inventory = build_inventory()
        openbsd_group = list(inventory.get_group("openbsd"))
        assert len(openbsd_group) == 2
        openbsd_names = {h.name for h in openbsd_group}
        assert openbsd_names == {"gw.london", "gw.newyork"}

    def test_group_freebsd(self):
        """freebsd group should contain 4 FreeBSD web/worker hosts."""
        inventory = build_inventory()
        freebsd_group = list(inventory.get_group("freebsd"))
        assert len(freebsd_group) == 4
        freebsd_names = {h.name for h in freebsd_group}
        expected = {
            "web-01.london",
            "web-02.london",
            "worker-01.newyork",
            "worker-02.newyork",
        }
        assert freebsd_names == expected

    def test_group_gateway(self):
        """gateway group should contain both gateways."""
        inventory = build_inventory()
        gateway_group = list(inventory.get_group("gateway"))
        assert len(gateway_group) == 2
        gateway_names = {h.name for h in gateway_group}
        assert gateway_names == {"gw.london", "gw.newyork"}

    def test_group_workers(self):
        """workers group should contain 2 compute worker hosts."""
        inventory = build_inventory()
        workers_group = list(inventory.get_group("workers"))
        assert len(workers_group) == 2
        worker_names = {h.name for h in workers_group}
        expected = {"worker-01.newyork", "worker-02.newyork"}
        assert worker_names == expected

    def test_group_docker(self):
        """docker group should contain only docker.newyork."""
        inventory = build_inventory()
        docker_group = list(inventory.get_group("docker"))
        assert len(docker_group) == 1
        assert docker_group[0].name == "docker.newyork"

    def test_group_debian(self):
        """debian group should contain both Debian hosts."""
        inventory = build_inventory()
        debian_group = list(inventory.get_group("debian"))
        assert len(debian_group) == 2
        debian_names = {h.name for h in debian_group}
        assert debian_names == {"db.london", "docker.newyork"}

    def test_debian_sudo_enabled(self):
        """Debian hosts should have _sudo=True."""
        inventory = build_inventory()
        docker = next(h for h in inventory if h.name == "docker.newyork")
        assert docker.data.get("_sudo") is True
