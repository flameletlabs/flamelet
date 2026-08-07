"""Tests for the pure network-config renderers.

These functions take a config dict and return file content. Nothing they do
raises on bad input — a wrong branch produces a syntactically plausible file
that simply does not bring the interface up, which is why they are worth
pinning. The `dhcp` coerced-to-`static` defect shipped in exactly this code and
rendered `iface eth1 inet static` with no address.

Assertions target STRUCTURE (a directive present with the right value) rather
than whole-file equality, so a cosmetic edit does not force a test rewrite.
"""

import pytest

from core.operations.debian_network import _build_interfaces_file
from core.operations.pf_gateway_routing import generate_pf_gateway_rules
from core.operations.wireguard import (
    _generate_wg_freebsd_config,
    _generate_wireguard_ini,
    _generate_wireguard_openbsd,
)

PUBKEY = "peerkeyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
PRIVKEY = "privkeyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
PSK = "pskAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def iface_block(text, name):
    """The lines belonging to one `iface <name> ...` stanza."""
    out, capturing = [], False
    for line in text.splitlines():
        if line.startswith(f"iface {name} "):
            capturing = True
            out.append(line)
        elif capturing and line.startswith(("iface ", "auto ")):
            break
        elif capturing:
            out.append(line)
    return "\n".join(out)


class TestInterfacesMethods:
    """static / manual / dhcp each render a different stanza shape."""

    def test_static_emits_address_and_gateway(self):
        cfg = {
            "interfaces": [
                {
                    "name": "eth0",
                    "method": "static",
                    "address": "10.0.0.10",
                    "netmask": "255.255.255.0",
                    "gateway": "10.0.0.1",
                }
            ]
        }
        block = iface_block(_build_interfaces_file(cfg), "eth0")
        assert "iface eth0 inet static" in block
        assert "address 10.0.0.10" in block
        assert "netmask 255.255.255.0" in block
        assert "gateway 10.0.0.1" in block

    @pytest.mark.parametrize("method", ["manual", "dhcp"])
    def test_manual_and_dhcp_emit_no_address_block(self, method):
        """The regression that shipped: dhcp was coerced to static and rendered
        `iface eth1 inet static` with no address — an invalid stanza."""
        cfg = {
            "interfaces": [
                {
                    "name": "eth1",
                    "method": method,
                    # present in config but must NOT be emitted for these methods
                    "address": "10.0.0.10",
                    "gateway": "10.0.0.1",
                }
            ]
        }
        block = iface_block(_build_interfaces_file(cfg), "eth1")
        assert f"iface eth1 inet {method}" in block
        assert "address" not in block, f"{method} must not emit an address"
        assert "gateway" not in block, f"{method} must not emit a gateway"

    def test_unknown_method_falls_back_to_static(self):
        cfg = {"interfaces": [{"name": "eth0", "method": "bogus", "address": "10.0.0.10"}]}
        assert "iface eth0 inet static" in _build_interfaces_file(cfg)


class TestInterfacesAddressFamily:
    """`type` is the ADDRESS FAMILY, not the interface role."""

    @pytest.mark.parametrize("family", ["inet", "inet6"])
    def test_valid_family_is_used(self, family):
        cfg = {"interfaces": [{"name": "eth0", "type": family, "method": "manual"}]}
        assert f"iface eth0 {family} manual" in _build_interfaces_file(cfg)

    @pytest.mark.parametrize("wrong", ["static", "bridge", "physical", ""])
    def test_role_shaped_value_does_not_produce_a_broken_line(self, wrong):
        """Config has previously set type to the ROLE, producing
        `iface eth0 static static`. It must fall back to inet instead."""
        cfg = {"interfaces": [{"name": "eth0", "type": wrong, "method": "static"}]}
        text = _build_interfaces_file(cfg)
        assert "iface eth0 inet static" in text
        assert f"iface eth0 {wrong} " not in text


class TestInterfacesBridge:
    def test_ports_render_bridge_directives(self):
        cfg = {
            "interfaces": [
                {
                    "name": "br0",
                    "method": "static",
                    "address": "10.0.0.2",
                    "ports": ["eth0", "eth1"],
                }
            ]
        }
        block = iface_block(_build_interfaces_file(cfg), "br0")
        assert "bridge-ports eth0 eth1" in block
        assert "bridge-stp off" in block

    def test_no_ports_means_no_bridge_directives(self):
        cfg = {"interfaces": [{"name": "eth0", "method": "static", "address": "10.0.0.2"}]}
        assert "bridge-ports" not in _build_interfaces_file(cfg)

    def test_loopback_is_always_emitted(self):
        assert "iface lo inet loopback" in _build_interfaces_file({"interfaces": []})

    def test_interface_without_a_name_is_skipped(self):
        cfg = {"interfaces": [{"method": "static", "address": "10.0.0.2"}]}
        text = _build_interfaces_file(cfg)
        assert "10.0.0.2" not in text

    def test_dns_search_accepts_list_or_string(self):
        base = {"name": "eth0", "method": "static", "address": "10.0.0.2"}
        as_list = _build_interfaces_file(
            {"interfaces": [{**base, "dns_search": ["a.example.com", "b.example.com"]}]}
        )
        as_str = _build_interfaces_file(
            {"interfaces": [{**base, "dns_search": "a.example.com b.example.com"}]}
        )
        assert "dns-search a.example.com b.example.com" in as_list
        assert "dns-search a.example.com b.example.com" in as_str


# --------------------------------------------------------------------------
# WireGuard: the same peer must render differently per OS.
# CLAUDE.md documents this and nothing tested it.
# --------------------------------------------------------------------------
WG_CONFIG = {
    "address": "10.100.0.2/24",
    "port": 51820,
    "private_key": PRIVKEY,
    "peers": [
        {
            "pubkey": PUBKEY,
            "allowed_ips": ["10.100.0.0/24", "10.0.0.0/24"],
            "endpoint": "vpn.example.com:51820",
            "keepalive": 25,
        }
    ],
}


class TestWireguardEndpointDiffersByOS:
    def test_ini_uses_colon_form(self):
        text = _generate_wireguard_ini(WG_CONFIG)
        assert "Endpoint = vpn.example.com:51820" in text

    def test_openbsd_uses_space_separated_form(self):
        """OpenBSD ifconfig wants `wgendpoint host port`, not host:port."""
        text = _generate_wireguard_openbsd(WG_CONFIG)
        assert "wgendpoint vpn.example.com 51820" in text
        assert "vpn.example.com:51820" not in text

    def test_freebsd_delegates_to_the_ini_renderer(self):
        assert _generate_wg_freebsd_config(WG_CONFIG) == _generate_wireguard_ini(WG_CONFIG)


class TestWireguardIni:
    def test_interface_section(self):
        text = _generate_wireguard_ini(WG_CONFIG)
        assert "[Interface]" in text
        assert "Address = 10.100.0.2/24" in text
        assert "ListenPort = 51820" in text
        assert f"PrivateKey = {PRIVKEY}" in text

    def test_allowed_ips_are_comma_separated(self):
        assert "AllowedIPs = 10.100.0.0/24, 10.0.0.0/24" in _generate_wireguard_ini(WG_CONFIG)

    def test_default_port_when_absent(self):
        assert "ListenPort = 51820" in _generate_wireguard_ini({"address": "10.0.0.1/24"})

    def test_optional_keys_are_omitted_not_blank(self):
        minimal = {
            "address": "10.0.0.1/24",
            "peers": [{"pubkey": PUBKEY, "allowed_ips": ["10.0.0.0/24"]}],
        }
        text = _generate_wireguard_ini(minimal)
        assert "PresharedKey" not in text
        assert "Endpoint" not in text
        assert "PersistentKeepalive" not in text

    def test_preshared_key_present_when_given(self):
        cfg = {**WG_CONFIG, "peers": [{**WG_CONFIG["peers"][0], "preshared_key": PSK}]}
        assert f"PresharedKey = {PSK}" in _generate_wireguard_ini(cfg)


class TestWireguardOpenbsd:
    def test_interface_line_shape(self):
        text = _generate_wireguard_openbsd(WG_CONFIG)
        assert text.splitlines()[0] == f"10.100.0.2/24 wgport 51820 wgkey {PRIVKEY}"

    def test_each_allowed_ip_gets_its_own_wgaip(self):
        text = _generate_wireguard_openbsd(WG_CONFIG)
        assert text.count("wgaip ") == 2

    def test_psk_precedes_allowed_ips(self):
        """OpenBSD requires wgpsk before wgaip; order is load-bearing."""
        cfg = {**WG_CONFIG, "peers": [{**WG_CONFIG["peers"][0], "preshared_key": PSK}]}
        text = _generate_wireguard_openbsd(cfg)
        assert text.index("wgpsk") < text.index("wgaip")

    def test_routes_are_appended_for_allowed_ips(self):
        text = _generate_wireguard_openbsd(WG_CONFIG, iface_name="wg1")
        assert "!/sbin/route add -inet 10.100.0.0/24 -link -iface wg1" in text

    def test_last_peer_line_has_no_trailing_continuation(self):
        """A dangling backslash before the route lines would break the file."""
        text = _generate_wireguard_openbsd(WG_CONFIG)
        peer_lines = [ln for ln in text.splitlines() if not ln.startswith("!/sbin/route")]
        assert not peer_lines[-1].rstrip().endswith("\\")

    def test_endpoint_without_a_port_is_passed_through(self):
        cfg = {**WG_CONFIG, "peers": [{**WG_CONFIG["peers"][0], "endpoint": "vpn.example.com"}]}
        assert "wgendpoint vpn.example.com" in _generate_wireguard_openbsd(cfg)


class TestPfGatewayRules:
    BASE = {
        "role": "gateway",
        "local_subnet": "10.10.0.0/24",
        "local_ip": "10.10.0.2",
        "vpn_interface": "tailscale0",
        "remote_subnets": ["10.20.0.0/24", "10.30.0.0/24"],
        "external_interface": "em0",
        "internal_bridge": "bridge10",
    }

    def test_macros_reflect_config(self):
        text = generate_pf_gateway_rules(self.BASE)
        assert 'ext_if = "em0"' in text
        assert 'vpn_if = "tailscale0"' in text
        assert 'bridge_if = "bridge10"' in text
        assert 'local_subnet = "10.10.0.0/24"' in text

    def test_remote_subnets_render_as_a_pf_list(self):
        text = generate_pf_gateway_rules(self.BASE)
        assert "{ 10.20.0.0/24, 10.30.0.0/24 }" in text

    def test_defaults_apply_when_keys_absent(self):
        text = generate_pf_gateway_rules({})
        assert 'vpn_if = "tailscale0"' in text
        assert 'ext_if = "em0"' in text

    @pytest.mark.xfail(
        reason="empty remote_subnets renders the pf list as '{  }'. pf rejects an "
        "empty list, so a gateway with no remote subnets yields an unloadable "
        "ruleset. Documented rather than silently accepted; fix belongs in a "
        "separate card.",
        strict=True,
    )
    def test_empty_remote_subnets_does_not_emit_an_empty_pf_list(self):
        text = generate_pf_gateway_rules({**self.BASE, "remote_subnets": []})
        assert "{  }" not in text
