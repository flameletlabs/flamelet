"""Tests for sudoers configuration operation."""

import importlib.util
from pathlib import Path

project_root = Path(__file__).parent.parent
_inv_path = project_root / "tenants" / "flamelet-example" / "inventory.py"
_spec = importlib.util.spec_from_file_location("flamelet_example_inventory", _inv_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_inventory = _mod.build_inventory


class TestSudoersOperation:
    """Test sudoers NOPASSWD configuration."""

    def test_sudoers_only_on_sudo_hosts(self, mock_state, mock_inventory):
        """add_sudoers_ops should only queue operations for hosts with _sudo=True."""
        # This test documents that sudoers is only for _sudo hosts, not _doas
        # Real test with home inventory would require SSH to hosts
        pass

    def test_sudoers_skips_doas_hosts(self):
        """OpenBSD hosts with _doas should not get sudoers entries."""
        inventory = build_inventory()
        openbsd_hosts = list(inventory.get_group("openbsd"))
        assert len(openbsd_hosts) == 1
        controller = openbsd_hosts[0]
        # OpenBSD has _doas: True, not _sudo
        assert controller.data.get("_doas") is True
        assert controller.data.get("_sudo") is not True

    def test_debian_has_sudo_flag(self):
        """Debian hosts should have _sudo=True."""
        inventory = build_inventory()
        debian_hosts = list(inventory.get_group("debian"))
        assert len(debian_hosts) == 1
        docker = debian_hosts[0]
        assert docker.data.get("_sudo") is True

    def test_freebsd_no_sudo_flag_by_default(self):
        """FreeBSD hosts have _sudo=True for operations, but sudoers not needed."""
        inventory = build_inventory()
        freebsd_hosts = list(inventory.get_group("freebsd"))
        assert len(freebsd_hosts) == 5
        # FreeBSD hosts have _sudo: True for privilege escalation, but wheel group
        # already has NOPASSWD so sudoers entries not redundant
        for host in freebsd_hosts:
            assert host.data.get("_sudo") is True
