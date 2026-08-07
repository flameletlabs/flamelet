"""Tests for the pure DNS config renderers: dnsmasq and unbound.

A DNS config that renders wrong takes a whole site off the network, and it does
so silently — the file writes fine and the daemon may still start. dnsmasq's
history in this repo (lease directories, rebind protection, zone forwarding,
DHCP option 3, systemd support) is the signature of code edited often and
checked by hand each time.

Assertions target directives rather than whole-file equality.
"""

import pytest

from core.operations.dnsmasq import _generate_dnsmasq_conf
from core.operations.unbound import _OS_DEFAULTS, _generate_unbound_conf, _generate_unbound_config

DNSMASQ_OS = {"conf_path": "/etc/dnsmasq.conf", "lease_path": "/var/lib/misc/dnsmasq.leases"}


def conf(config, os_defaults=None):
    return _generate_dnsmasq_conf(config, os_defaults or DNSMASQ_OS)


class TestDnsmasqListening:
    def test_defaults_when_config_is_empty(self):
        text = conf({})
        assert "port=53" in text
        assert "listen-address=127.0.0.1" in text

    def test_explicit_listen_addresses(self):
        text = conf({"listen": ["127.0.0.1", "10.0.0.1"]})
        assert "listen-address=127.0.0.1" in text
        assert "listen-address=10.0.0.1" in text

    def test_interface_accepts_a_bare_string_or_a_list(self):
        assert "interface=eth0" in conf({"interface": "eth0"})
        both = conf({"interface": ["eth0", "eth1"]})
        assert "interface=eth0" in both and "interface=eth1" in both

    def test_bind_interfaces_flag(self):
        assert "bind-interfaces" in conf({"bind_interfaces": True})
        assert "bind-interfaces" not in conf({"bind_interfaces": False})

    def test_port_zero_is_emitted_because_it_disables_dns(self):
        """dnsmasq treats port=0 as "disable DNS, run DHCP only". A falsy
        check used to drop the line, silently leaving DNS on 53."""
        assert "port=0" in conf({"port": 0})


class TestDnsmasqUpstreamAndRecords:
    def test_no_resolv(self):
        assert "no-resolv" in conf({"no_resolv": True})
        assert "no-resolv" not in conf({})

    def test_servers_key_emits_upstream_servers(self):
        assert "server=1.1.1.1" in conf({"servers": ["1.1.1.1"]})

    def test_server_key_emits_zone_forwarding(self):
        assert "server=/london/10.0.0.2" in conf({"server": ["/london/10.0.0.2"]})

    def test_both_server_keys_are_honoured_together(self):
        """`servers` (upstream) and `server` (zone forwarding) are distinct keys
        one character apart that both render `server=`. Pinning it so the
        overlap is deliberate rather than discovered."""
        text = conf({"servers": ["1.1.1.1"], "server": ["/london/10.0.0.2"]})
        assert "server=1.1.1.1" in text
        assert "server=/london/10.0.0.2" in text

    def test_static_a_records(self):
        assert "address=/host.example.com/10.0.0.5" in conf(
            {"address": ["/host.example.com/10.0.0.5"]}
        )

    def test_local_zones_prevent_root_queries(self):
        """Marks private zones so dnsmasq 2.93+ does not query ICANN roots."""
        assert "local=/london/" in conf({"local": ["/london/"]})


class TestDnsmasqOptions:
    def test_cache_size_defaults_when_any_option_is_set(self):
        assert "cache-size=10000" in conf({"options": {"log_queries": True}})
        assert "cache-size=500" in conf({"options": {"cache_size": 500}})

    def test_an_empty_options_dict_emits_no_options_block_at_all(self):
        """The whole block is guarded by a truthiness check, so `options: {}`
        yields no cache-size — dnsmasq falls back to its own default of 150,
        not the 10000 this renderer uses. Surprising, but deliberate to pin:
        the default only applies once at least one option is set."""
        text = conf({"options": {}})
        assert "cache-size" not in text

    def test_logging_flags(self):
        text = conf({"options": {"log_queries": True, "log_dhcp": True}})
        assert "log-queries" in text
        assert "log-dhcp" in text
        off = conf({"options": {"cache_size": 500}})
        assert "log-queries" not in off and "log-dhcp" not in off

    def test_dhcp_fqdn_forces_a_domain(self):
        """dhcp-fqdn is invalid without a domain, so one is always emitted."""
        assert "domain=local" in conf({"options": {"dhcp_fqdn": True}})
        assert "domain=example.com" in conf(
            {"options": {"dhcp_fqdn": True, "domain": "example.com"}}
        )

    def test_dhcp_authoritative(self):
        assert "dhcp-authoritative" in conf({"options": {"dhcp_authoritative": True}})


class TestDnsmasqRebindProtection:
    def test_selective_rebind_domains_are_whitelisted(self):
        text = conf({"options": {"rebind_domains": ["london", "newyork"]}})
        assert "rebind-domain-ok=london" in text
        assert "rebind-domain-ok=newyork" in text

    def test_disabling_protection_suppresses_the_whitelist(self):
        """The two are mutually exclusive branches — with protection disabled the
        per-domain whitelist is meaningless and must not be emitted."""
        text = conf({"options": {"disable_rebind_protection": True, "rebind_domains": ["london"]}})
        assert "rebind-domain-ok" not in text


class TestDnsmasqDhcp:
    SUBNET = {"start": "10.20.0.128", "end": "10.20.0.200", "lease": "12h"}

    def test_accepts_a_single_dict(self):
        assert "dhcp-range=10.20.0.128,10.20.0.200,12h" in conf({"dhcp": self.SUBNET})

    def test_accepts_a_list_of_subnets(self):
        second = {"start": "10.30.0.10", "end": "10.30.0.50", "lease": "6h"}
        text = conf({"dhcp": [self.SUBNET, second]})
        assert "dhcp-range=10.20.0.128,10.20.0.200,12h" in text
        assert "dhcp-range=10.30.0.10,10.30.0.50,6h" in text

    def test_lease_defaults_to_12h(self):
        assert "dhcp-range=10.20.0.1,10.20.0.9,12h" in conf(
            {"dhcp": {"start": "10.20.0.1", "end": "10.20.0.9"}}
        )

    def test_incomplete_range_is_skipped(self):
        assert "dhcp-range=" not in conf({"dhcp": {"start": "10.20.0.1"}})

    def test_router_option_carries_the_address(self):
        """A bare `dhcp-option=3` advertises no router. The address form is the
        fix that had to be made once already."""
        text = conf({"dhcp": {**self.SUBNET, "router": "10.20.0.1"}})
        assert "dhcp-option=3,10.20.0.1" in text

    def test_router_is_taken_from_the_first_subnet_that_declares_one(self):
        text = conf({"dhcp": [self.SUBNET, {**self.SUBNET, "router": "10.30.0.1"}]})
        assert "dhcp-option=3,10.30.0.1" in text


class TestDnsmasqRfc2136:
    def test_update_allowed_entries(self):
        text = conf({"dhcp_update": {"enabled": True, "allow_update": ["10.0.0.0/24"]}})
        assert "update-allowed=10.0.0.0/24" in text

    def test_disabled_emits_nothing(self):
        assert "update-allowed" not in conf({"dhcp_update": {"enabled": False}})

    def test_default_allow_update_is_loopback(self):
        assert "update-allowed=127.0.0.1" in conf({"dhcp_update": {"enabled": True}})


# --------------------------------------------------------------------------
# unbound
# --------------------------------------------------------------------------
class TestUnboundBaseBlock:
    @pytest.mark.parametrize("os_key", sorted(_OS_DEFAULTS))
    def test_paths_come_from_the_os_defaults(self, os_key):
        """chroot/directory/pidfile/username differ per OS; a hardcoded path
        would write a valid config to the wrong place."""
        d = _OS_DEFAULTS[os_key]
        text = _generate_unbound_conf({}, d)
        assert f'chroot: "{d["chroot"]}"' in text
        assert f'directory: "{d["directory"]}"' in text
        assert f'pidfile: "{d["pidfile"]}"' in text
        assert f'username: "{d["username"]}"' in text

    def test_hardening_defaults_are_always_present(self):
        text = _generate_unbound_conf({}, _OS_DEFAULTS["Linux"])
        for directive in ("hide-identity: yes", "hide-version: yes", "do-ip6: no"):
            assert directive in text

    def test_convenience_wrapper_uses_linux_defaults(self):
        assert _generate_unbound_config({}) == _generate_unbound_conf({}, _OS_DEFAULTS["Linux"])


class TestUnboundAccessControl:
    def test_base_rules_are_present(self):
        text = _generate_unbound_conf({}, _OS_DEFAULTS["Linux"])
        assert "access-control: 0.0.0.0/0 refuse" in text
        assert "access-control: 127.0.0.0/8 allow" in text

    def test_extra_rules_are_added(self):
        text = _generate_unbound_conf(
            {"access_control": ["10.0.0.0/24 allow"]}, _OS_DEFAULTS["Linux"]
        )
        assert "access-control: 10.0.0.0/24 allow" in text

    def test_a_rule_matching_a_base_rule_is_not_duplicated(self):
        """A duplicate refuse rule is harmless but a duplicated allow can mask
        intent; the renderer dedupes and that behaviour is pinned."""
        text = _generate_unbound_conf(
            {"access_control": ["0.0.0.0/0 refuse", "127.0.0.0/8 allow"]},
            _OS_DEFAULTS["Linux"],
        )
        assert text.count("access-control: 0.0.0.0/0 refuse") == 1
        assert text.count("access-control: 127.0.0.0/8 allow") == 1


class TestUnboundData:
    def test_listen_defaults_to_loopback(self):
        assert "interface: 127.0.0.1" in _generate_unbound_conf({}, _OS_DEFAULTS["Linux"])

    def test_local_data_records(self):
        text = _generate_unbound_conf(
            {
                "local_data": [
                    {"name": "host.example.com.", "type": "A", "value": "10.0.0.10"},
                    {"name": "alias.example.com.", "type": "CNAME", "value": "host.example.com."},
                ]
            },
            _OS_DEFAULTS["Linux"],
        )
        assert 'local-data: "host.example.com. IN A 10.0.0.10"' in text
        assert 'local-data: "alias.example.com. IN CNAME host.example.com."' in text

    def test_local_data_type_defaults_to_a(self):
        text = _generate_unbound_conf(
            {"local_data": [{"name": "host.example.com.", "value": "10.0.0.10"}]},
            _OS_DEFAULTS["Linux"],
        )
        assert "IN A 10.0.0.10" in text

    def test_forward_zones(self):
        text = _generate_unbound_conf(
            {"forward_zones": [{"name": ".", "addrs": ["1.1.1.1", "8.8.8.8"]}]},
            _OS_DEFAULTS["Linux"],
        )
        assert "forward-zone:" in text
        assert 'name: "."' in text
        assert "forward-addr: 1.1.1.1" in text
        assert "forward-addr: 8.8.8.8" in text

    def test_no_forward_zone_block_when_none_configured(self):
        assert "forward-zone:" not in _generate_unbound_conf({}, _OS_DEFAULTS["Linux"])
