"""Tests for the bhyve and bastille pure helpers.

_parse_size_bytes is the priority. Size-suffix parsers are a classic defect
magnet, and getting one wrong does not raise — it silently provisions a VM with
the wrong disk or memory. These tests pin both the conversions and, just as
importantly, what happens to junk.
"""

import pytest

from core.operations.bastille import _sysrc
from core.operations.bhyve import (
    _build_vm_create_command,
    _generate_cloud_init_user_data,
    _parse_size_bytes,
)

K, M, G, T = 1024, 1024**2, 1024**3, 1024**4


class TestParseSizeUnits:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("2K", 2 * K),
            ("512M", 512 * M),
            ("20G", 20 * G),
            ("1T", 1 * T),
        ],
    )
    def test_each_unit_multiplies_correctly(self, text, expected):
        assert _parse_size_bytes(text) == expected

    @pytest.mark.parametrize("text", ["20g", "20G", " 20G ", "20 G"])
    def test_case_and_surrounding_whitespace_are_tolerated(self, text):
        """Lowercase is upper-cased and the string is stripped. '20 G' works
        because int() tolerates the trailing space left behind."""
        assert _parse_size_bytes(text) == 20 * G

    def test_a_unitless_number_is_rejected(self):
        """It used to be accepted AS BYTES, so "20" provisioned a disk 2**30
        times smaller than the "20G" that was meant, and nothing complained."""
        with pytest.raises(ValueError) as exc:
            _parse_size_bytes("20")
        assert "unit suffix" in str(exc.value)

    def test_zero_is_preserved(self):
        assert _parse_size_bytes("0G") == 0


class TestParseSizeRejectsJunk:
    """Every malformed input raises ValueError naming the problem. Two of these
    previously did not: a negative size returned a negative byte count, and an
    empty string raised IndexError from indexing off the end — which reads as a
    bug in flamelet rather than a bad value in tenant config."""

    @pytest.mark.parametrize(
        "text,fragment",
        [
            ("-5G", "negative"),
            ("", "empty"),
            (None, "empty"),
            ("20", "unit suffix"),
            ("20GB", "unit suffix"),
            ("20X", "unit suffix"),
        ],
    )
    def test_malformed_input_raises_value_error(self, text, fragment):
        with pytest.raises(ValueError) as exc:
            _parse_size_bytes(text)
        assert fragment in str(exc.value)

    def test_fractional_size_raises(self):
        """Still a ValueError, from int() — the type callers can rely on."""
        with pytest.raises(ValueError):
            _parse_size_bytes("1.5G")

    def test_valid_sizes_still_parse(self):
        """Control: the rejection is conditional, not a blanket refusal."""
        assert _parse_size_bytes("20G") == 20 * G
        assert _parse_size_bytes("0G") == 0


class TestVmCreateCommand:
    ARGS = dict(
        vm_name="vm-01",
        vcpu=4,
        memory="4G",
        disk_size="20G",
        image="/zfs/images/debian.raw",
        network_config="ip=10.0.0.10/24;gateway4=10.0.0.1",
    )

    def test_command_starts_with_vm_create(self):
        cmd = _build_vm_create_command(**self.ARGS)
        assert cmd.startswith("vm create")

    def test_all_supplied_values_appear(self):
        cmd = _build_vm_create_command(**self.ARGS)
        for value in ("vm-01", "4G", "20G", "/zfs/images/debian.raw"):
            assert value in cmd, f"{value} missing from the command"
        assert "4" in cmd  # vcpu

    def test_template_default_and_override(self):
        assert "uefi-raw" in _build_vm_create_command(**self.ARGS)
        assert "custom-tpl" in _build_vm_create_command(**self.ARGS, template="custom-tpl")

    def test_ssh_key_flag_is_not_used(self):
        """The -k flag is deliberately avoided: it does not work reliably with
        vm-bhyve 1.7.0, so keys go in via cloud-init write_files instead."""
        cmd = _build_vm_create_command(**self.ARGS)
        assert " -k " not in cmd


class TestCloudInitUserData:
    def test_is_a_cloud_config_document(self):
        assert _generate_cloud_init_user_data("ssh-ed25519 AAAAC3Nz example").startswith(
            "#cloud-config"
        )

    def test_public_key_is_embedded(self):
        key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 user@example.com"
        assert key in _generate_cloud_init_user_data(key)

    def test_no_key_still_produces_a_valid_document(self):
        assert _generate_cloud_init_user_data().startswith("#cloud-config")

    def test_only_a_public_key_is_ever_embedded(self):
        """Guard against a private key being passed in and written to the VM.
        The parameter is named ssh_public_key_content for a reason."""
        out = _generate_cloud_init_user_data("ssh-ed25519 AAAAC3Nz example")
        assert "PRIVATE KEY" not in out


class TestBastilleSysrc:
    def test_renders_a_bastille_sysrc_command(self):
        assert _sysrc("db", "sshd_enable", "YES") == 'bastille sysrc db sshd_enable="YES"'

    def test_value_is_quoted_so_spaces_survive(self):
        """Unquoted, a value with a space would be parsed as extra arguments."""
        cmd = _sysrc("db", "ifconfig_epair0", "inet 10.0.0.5 netmask 255.255.255.0")
        assert cmd.endswith('ifconfig_epair0="inet 10.0.0.5 netmask 255.255.255.0"')

    def test_empty_value_is_still_quoted(self):
        """sysrc key="" clears a value; an unquoted empty string would drop the
        argument entirely and change the meaning."""
        assert _sysrc("db", "extra", "") == 'bastille sysrc db extra=""'
