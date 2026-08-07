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

    def test_a_bare_number_is_bytes_not_gigabytes(self):
        """Worth pinning explicitly: "20" is twenty BYTES. A config that omits
        the unit gets a VM 2^30 times smaller than intended, and nothing
        complains."""
        assert _parse_size_bytes("20") == 20

    def test_zero_is_preserved(self):
        assert _parse_size_bytes("0G") == 0


class TestParseSizeRejectsJunk:
    """Junk raises rather than silently returning a wrong number. The exception
    types are incidental — what matters is that none of these return a value."""

    @pytest.mark.parametrize(
        "text,exc",
        [
            ("20GB", ValueError),  # trailing B is not a recognised unit
            ("1.5G", ValueError),  # fractional sizes unsupported
            ("20X", ValueError),  # unknown unit
            ("", IndexError),  # empty string indexes off the end
        ],
    )
    def test_malformed_input_raises(self, text, exc):
        with pytest.raises(exc):
            _parse_size_bytes(text)

    def test_none_raises(self):
        with pytest.raises(AttributeError):
            _parse_size_bytes(None)

    @pytest.mark.xfail(
        reason="a negative size is accepted and returns a NEGATIVE byte count "
        "instead of raising — the one input that is silently wrong rather than "
        "loud. It would be passed straight to `vm create` as a disk or memory "
        "size. Recorded rather than fixed inline; adding a guard is a behaviour "
        "change and belongs in its own card.",
        strict=True,
    )
    def test_negative_size_is_rejected(self):
        with pytest.raises(ValueError):
            _parse_size_bytes("-5G")


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
