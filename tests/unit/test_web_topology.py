"""Tests for the topology endpoint in core/web/api/services.py.

The hub of a WireGuard topology is derived structurally — it is the node whose
peers carry "spoke" comments — rather than matched against a known hostname.
These tests pin that down: the same topology must produce the same graph no
matter what the hosts are called.
"""

import asyncio
import re
from pathlib import Path

import pytest

from core.web.api import services

HUB_PUBKEY = "hubkeyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
SPOKE1_PUBKEY = "spoke1keyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
SPOKE2_PUBKEY = "spoke2keyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def build_configs(hub="hub-01.example.com", spokes=("s1.example.com", "s2.example.com")):
    """A minimal hub-and-spoke WireGuard config, parameterised by hostname."""
    s1, s2 = spokes
    wireguard = {
        hub: {
            "interfaces": {
                "wg0": {
                    "address": "10.0.0.1/24",
                    "peers": [
                        {"pubkey": SPOKE1_PUBKEY, "comment": f"{s1} spoke"},
                        {"pubkey": SPOKE2_PUBKEY, "comment": f"{s2} spoke"},
                    ],
                }
            }
        },
        s1: {"interfaces": {"wg0": {"address": "10.0.0.2/24", "peers": [{"pubkey": HUB_PUBKEY}]}}},
        s2: {"interfaces": {"wg0": {"address": "10.0.0.3/24", "peers": [{"pubkey": HUB_PUBKEY}]}}},
    }
    return wireguard


def run_topology(monkeypatch, wireguard, autossh=None, aliases=None):
    """Invoke get_topology with the given configs injected."""
    configs = {"WIREGUARD": wireguard, "AUTOSSH_TUNNELS": autossh or {}}
    if aliases is not None:
        configs["ENDPOINT_ALIASES"] = aliases

    def fake_load(tenant_path, attr_name):
        if attr_name not in configs:
            raise FileNotFoundError(attr_name)
        return configs[attr_name]

    monkeypatch.setattr(services, "get_tenant_path", lambda name: Path("/nonexistent"))
    monkeypatch.setattr(services, "load_service_config", fake_load)
    return asyncio.run(services.get_topology("any-tenant"))


def edge(result, frm, to):
    for e in result["edges"]:
        if e["from"] == frm and e["to"] == to:
            return e
    return None


class TestHubDerivation:
    def test_hub_detected_regardless_of_hostname(self, monkeypatch):
        """A hub named anything at all is still recognised as the hub."""
        for hub in ("hub-01.example.com", "zzz", "gateway.internal", "a.b.c.d.e"):
            result = run_topology(monkeypatch, build_configs(hub=hub))
            assert edge(result, "s1.example.com", hub) is not None, f"hub {hub!r} was not derived"

    def test_spoke_to_hub_direction(self, monkeypatch):
        """Spoke→hub edges are spoke-to-hub; hub→spoke edges are not."""
        hub = "gateway.internal"
        result = run_topology(monkeypatch, build_configs(hub=hub))

        assert edge(result, "s1.example.com", hub)["direction"] == "spoke-to-hub"
        assert edge(result, "s2.example.com", hub)["direction"] == "spoke-to-hub"
        assert edge(result, hub, "s1.example.com")["direction"] == "peer-to-peer"

    def test_result_is_isomorphic_under_renaming(self, monkeypatch):
        """Renaming every host reshapes labels but not the graph's structure.

        This is the real regression guard: a hostname hardcoded anywhere in the
        derivation would make one of these two runs differ in shape.
        """

        def shape(result):
            return sorted((e["direction"], e["type"], e["interface"]) for e in result["edges"])

        a = run_topology(
            monkeypatch,
            build_configs(hub="hub-01.example.com", spokes=("s1.example.com", "s2.example.com")),
        )
        b = run_topology(
            monkeypatch, build_configs(hub="totally-different", spokes=("x.other", "y.other"))
        )
        assert shape(a) == shape(b)
        assert len(a["nodes"]) == len(b["nodes"]) == 3

    def test_spoke_only_topology_has_no_hub(self, monkeypatch):
        """With no "spoke" comments anywhere, nothing is treated as a hub."""
        wireguard = {
            "a.example.com": {
                "interfaces": {
                    "wg0": {"address": "10.0.0.1/24", "peers": [{"pubkey": SPOKE1_PUBKEY}]}
                }
            },
            "b.example.com": {
                "interfaces": {"wg0": {"address": "10.0.0.2/24", "peers": [{"pubkey": HUB_PUBKEY}]}}
            },
        }
        result = run_topology(monkeypatch, wireguard)
        assert result["edges"] == []
        assert not any(e["direction"] == "spoke-to-hub" for e in result["edges"])

    def test_two_hubs_do_not_invent_edges(self, monkeypatch):
        """With two hubs, an unresolvable peer is skipped rather than guessed."""
        wireguard = build_configs(hub="hub-a")
        # Give the second config its own spoke comment so it also reads as a hub.
        wireguard["s1.example.com"]["interfaces"]["wg0"]["peers"] = [
            {"pubkey": SPOKE2_PUBKEY, "comment": "s2.example.com spoke"}
        ]
        result = run_topology(monkeypatch, wireguard)

        # s2 points at HUB_PUBKEY, which belongs to neither derived hub. With two
        # hubs the code must not pick one at random.
        assert edge(result, "s2.example.com", "hub-a") is None
        assert edge(result, "s2.example.com", "s1.example.com") is None


class TestEndpointAliases:
    def test_missing_aliases_config_is_identity(self, monkeypatch):
        """A tenant with no ENDPOINT_ALIASES still resolves tunnels, unmapped."""
        autossh = {
            "tun1": {
                "deploy_to": ["s1.example.com"],
                "remote_host": "vpn.example.com",
                "local_port": 2222,
            }
        }
        result = run_topology(monkeypatch, build_configs(), autossh=autossh)
        e = edge(result, "s1.example.com", "vpn.example.com")
        assert e is not None
        assert e["type"] == "autossh"
        assert e["remote_host"] == "vpn.example.com"

    def test_alias_maps_public_endpoint_to_internal_host(self, monkeypatch):
        autossh = {
            "tun1": {
                "deploy_to": ["s1.example.com"],
                "remote_host": "vpn.example.com",
                "local_port": 2222,
            }
        }
        result = run_topology(
            monkeypatch,
            build_configs(hub="gateway.internal"),
            autossh=autossh,
            aliases={"vpn.example.com": "gateway.internal"},
        )
        e = edge(result, "s1.example.com", "gateway.internal")
        assert e is not None
        # The public name is still reported, only the graph node is remapped.
        assert e["remote_host"] == "vpn.example.com"

    @pytest.mark.parametrize("bad", ["a string", 42, ["a", "list"]])
    def test_non_dict_aliases_is_ignored(self, monkeypatch, bad):
        """A malformed ENDPOINT_ALIASES degrades to identity, it does not crash."""
        autossh = {
            "tun1": {
                "deploy_to": ["s1.example.com"],
                "remote_host": "vpn.example.com",
                "local_port": 2222,
            }
        }
        result = run_topology(monkeypatch, build_configs(), autossh=autossh, aliases=bad)
        assert edge(result, "s1.example.com", "vpn.example.com") is not None


class TestNoHardcodedInfrastructure:
    """Guard against a real hostname being hardcoded in this module again.

    The endpoint used to branch on a literal hostname from one real network,
    which both leaked private infrastructure into a public repo and silently
    failed for every other tenant. These checks describe the *shape* of that
    defect rather than listing the specific names that caused it — naming them
    here would put them back in the repo, and would only catch those five.
    """

    # Domains that are safe to appear in a public repository.
    APPROVED = (
        "example.com",
        "example.net",
        "example.org",
        ".internal",
        ".local",
        ".invalid",
        ".test",
    )

    def _source(self):
        return Path(services.__file__).read_text()

    def test_no_hostname_shaped_string_literal(self):
        """No quoted string may look like a hostname unless it is an example.

        This is the precise shape of the original bug: a hostname sitting in a
        string literal and compared against config keys.
        """
        literals = re.findall(r"""["']([^"'\n]+)["']""", self._source())
        suspects = [
            s
            for s in literals
            if re.fullmatch(r"[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+", s)
            and not s.endswith(self.APPROVED)
        ]
        assert not suspects, f"hostname-shaped literal(s) in services.py: {suspects}"

    def test_no_unapproved_fqdn_anywhere(self):
        """Comments and docstrings are as public as code — check them too."""
        found = re.findall(
            r"\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+"
            r"(?:com|net|org|io|dev|internal|local|lan|invalid|test)\b",
            self._source(),
        )
        suspects = sorted({f for f in found if not f.endswith(self.APPROVED)})
        assert not suspects, f"unapproved FQDN(s) in services.py: {suspects}"

    def test_guard_catches_a_planted_hostname(self):
        """The two checks above must actually fail on a real violation.

        Without this, both could pass by matching nothing at all.
        """
        planted = 'peer_host = "gw-01.corp"\n# see gw-01.corp for details\n'
        literals = re.findall(r"""["']([^"'\n]+)["']""", planted)
        assert any(
            re.fullmatch(r"[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+", s)
            and not s.endswith(self.APPROVED)
            for s in literals
        )
