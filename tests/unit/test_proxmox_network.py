"""Tests for proxmox network verification.

_configure_bridge and _configure_bond VERIFY that an interface exists; they
never build one. They used to accept ports/address/netmask/gateway/slaves and
silently ignore them, so a tenant could declare a bridge address, see the
deploy report success, and believe the hypervisor was configured. These tests
pin the refusal down so the silent-ignore behaviour cannot come back.
"""

import pytest

from core.operations import proxmox


class TestRejectsKeysItCannotApply:
    @pytest.mark.parametrize(
        "key,value",
        [
            ("address", "10.0.0.2"),
            ("netmask", "255.255.255.0"),
            ("gateway", "10.0.0.1"),
            ("ports", ["nic0"]),
        ],
    )
    def test_bridge_rejects_build_time_key(self, key, value):
        with pytest.raises(ValueError) as exc:
            proxmox._configure_bridge(None, None, {"iface": "vmbr0", key: value})
        msg = str(exc.value)
        assert key in msg, "the error must name the offending key"
        assert "debian-network" in msg, "the error must say where to define it instead"

    def test_bond_rejects_slaves(self):
        with pytest.raises(ValueError) as exc:
            proxmox._configure_bond(None, None, {"iface": "bond0", "slaves": ["eth0"]})
        assert "slaves" in str(exc.value)

    def test_error_names_every_offending_key_at_once(self):
        """A config with several bad keys reports all of them, not just the first."""
        spec = {"iface": "vmbr0", "address": "10.0.0.2", "gateway": "10.0.0.1"}
        with pytest.raises(ValueError) as exc:
            proxmox._configure_bridge(None, None, spec)
        assert "address" in str(exc.value)
        assert "gateway" in str(exc.value)

    @pytest.mark.parametrize("empty", [None, "", [], {}])
    def test_present_but_empty_keys_are_not_rejected(self, empty):
        """An unset or empty key must not trip the guard.

        Tests the pure guard directly rather than going through _configure_*,
        so a pass means "no error was raised" and nothing else.
        """
        proxmox._reject_unapplied_keys(
            "bridge",
            "vmbr0",
            {"iface": "vmbr0", "address": empty, "ports": empty},
            proxmox._BRIDGE_UNAPPLIED,
        )

    def test_verification_only_spec_is_accepted(self):
        """iface + type alone is the supported shape and must pass cleanly."""
        proxmox._reject_unapplied_keys(
            "bridge", "vmbr0", {"iface": "vmbr0", "type": "bridge"}, proxmox._BRIDGE_UNAPPLIED
        )

    def test_guard_fires_on_a_populated_key(self):
        """Control: the guard must reject when a value IS present.

        Without this, the two tests above would pass just as happily against a
        guard that never raises at all.
        """
        with pytest.raises(ValueError):
            proxmox._reject_unapplied_keys(
                "bridge", "vmbr0", {"address": "10.0.0.2"}, proxmox._BRIDGE_UNAPPLIED
            )


class TestVerificationCanActuallyFail:
    def test_bridge_check_has_no_always_true_fallback(self):
        """`ip link show` must not be followed by `|| echo`.

        The previous command ended in `|| echo 'not found'`, so it exited 0 even
        when the bridge was missing: it printed a verdict it could never act on.
        A verification that cannot fail is not a verification.
        """
        source = __import__("inspect").getsource(proxmox)
        assert "|| echo 'Bridge" not in source
        assert "|| echo 'Bond" not in source
        assert 'commands=[f"ip link show {iface}"]' in source
