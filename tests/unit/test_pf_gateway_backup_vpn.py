"""The backup VPN interface must be genuinely optional.

It used to default to "wg0" and its rules were emitted whenever remote_subnets
was non-empty, so a gateway with no backup VPN had no way to say so: omitting the
key produced NAT and pass rules for an interface that did not exist.

That is not cosmetic. A real deployment ran for months with three
`nat on tailscale0` rules after Tailscale had been uninstalled, and the only way
to remove them was to name a DIFFERENT dead interface. Rules referencing an
absent interface are dead weight in a firewall people read when debugging, and
they imply a redundancy path that is not there.

These assert the two branches by rendering through the real operation.
"""

import re

from core.operations import pf_gateway_routing as pfgr


def _render(config):
    """Return the generated pf.conf text for a gateway config."""
    return pfgr.generate_pf_gateway_rules(config)


BASE = {
    "role": "gateway",
    "local_subnet": "10.0.0.0/24",
    "local_ip": "10.0.0.2",
    "vpn_interface": "wt0",
    "remote_subnets": ["10.1.0.0/24"],
    "external_interface": "em0",
    "internal_bridge": "bridge0",
}


class TestBackupVpnOptional:
    def test_omitted_emits_no_backup_rules(self):
        """The regression: no key must mean no rules, not rules for a default."""
        conf = _render(dict(BASE))

        assert "wt0" in conf, "primary VPN rules should still be present"
        # No rule may reference an interface we never configured.
        for line in conf.splitlines():
            if line.strip().startswith(("nat on", "pass out on", "pass in on")):
                assert "wg0" not in line, f"emitted a rule for an unconfigured wg0: {line}"
                assert "tailscale0" not in line, f"emitted a stale tailscale0 rule: {line}"

    def test_present_emits_backup_rules(self):
        """A tenant that DOES have a backup VPN still gets its rules."""
        conf = _render(dict(BASE, backup_vpn="wg0"))

        assert re.search(r"^nat on wg0 ", conf, re.M), "backup NAT rule missing"
        assert re.search(r"^pass out on wg0 ", conf, re.M), "backup pass-out rule missing"
        assert re.search(r"^pass in on wg0 ", conf, re.M), "backup pass-in rule missing"

    def test_empty_string_counts_as_absent(self):
        """`backup_vpn: ""` is how a tenant disables it without deleting the key."""
        conf = _render(dict(BASE, backup_vpn=""))

        assert not re.search(r"^nat on  ", conf, re.M), "rendered a rule with an empty interface"
        for line in conf.splitlines():
            if line.strip().startswith("nat on"):
                assert line.split()[2], f"rule has no interface: {line}"

    def test_no_remote_subnets_still_emits_no_vpn_rules(self):
        """Pre-existing behaviour that must not regress: pf rejects `{  }`."""
        conf = _render(dict(BASE, remote_subnets=[], backup_vpn="wg0"))

        assert "{  }" not in conf, "empty list literal would make the ruleset fail to load"
