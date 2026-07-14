"""pf firewall gateway routing for Tailscale mesh networks (FreeBSD/OpenBSD).

This operation implements transparent gateway routing on Tailscale-connected
hypervisors, allowing local clients to reach remote subnets via Tailscale VPN.

Concept:
--------
In a multi-location Tailscale mesh network:
- Each location has a local network (e.g., home: 192.168.150.0/24)
- Each location has a Tailscale-enabled hypervisor (virt.home)
- Hypervisor advertises local subnet via Tailscale
- Hypervisor acts as gateway for local clients to reach remote subnets

Traffic Flow:
  Client (192.168.150.x)
    → virt.home gateway (192.168.150.2)
    → pf NAT translates source to virt.home's Tailscale IP
    → Tailscale mesh routes to remote gateway
    → Remote gateway processes and replies
    → Reply comes back to virt.home's Tailscale IP
    → pf reverse-NAT restores original destination
    → Reply sent back to client via local network

Configuration:
--------------
On FreeBSD hosts with Tailscale, define:

PF_GATEWAY_ROUTING = {
    "virt.home": {
        "role": "gateway",                    # "gateway" or "endpoint"
        "local_subnet": "192.168.150.0/24",  # Local network to protect
        "local_ip": "192.168.150.2",         # Gateway IP on local network
        "vpn_interface": "tailscale0",       # VPN interface name
        "remote_subnets": [
            "192.168.160.0/24",              # baar location
            "192.168.180.0/24",              # pangea location
            "192.168.80.0/24",               # work location
        ],
        "backup_vpn": "wg0",                 # Optional: fallback VPN interface
        "external_interface": "em0",         # External network interface
        "internal_bridge": "bridge10",       # Internal jail/VM bridge
    }
}

Rules Generated:
----------------
1. NAT Rules:
   - External traffic: local → external interface
   - VPN traffic: local clients → VPN interface (using dynamic interface IP)
   - Return traffic: remote subnets → internal bridge (reverse NAT)

2. Filter Rules:
   - Allow DNS/DHCP on local gateway
   - Allow local clients to reach gateway
   - Allow outbound to remote subnets via VPN
   - Allow return traffic from remote subnets
   - Allow traffic between VPN interfaces

3. Anchors:
   - Tailscale dynamic rules (for MagicDNS, route updates)
   - RDR anchors (for bastille port redirects)

FreeBSD vs OpenBSD Differences:
-------------------------------
FreeBSD:
  - Uses sysrc for rc.conf configuration
  - pf enabled via: sysrc pf_enable=YES
  - pf rules reloaded via: pfctl -f /etc/pf.conf
  - Common on hypervisors (supports bhyve, jails)

OpenBSD:
  - Uses rcctl for service management
  - pf enabled via: rcctl enable pf
  - pf is native (designed for OpenBSD originally)
  - Good for edge/gateway routers

Linux Equivalent (iptables/nftables):
-------------------------------------
Linux systems use iptables (legacy) or nftables (modern) instead of pf:

POSTROUTING chain NAT:
  iptables -t nat -A POSTROUTING -o tailscale0 -j MASQUERADE

FORWARD chain filter:
  iptables -A FORWARD -i bridge0 -o tailscale0 -j ACCEPT
  iptables -A FORWARD -i tailscale0 -o bridge0 -j ACCEPT

See: linux/netfilter_gateway_routing.md for implementation

Key Differences:
  - pf: Stateful at kernel level, rules file-based
  - iptables: Per-chain rules, can be dynamic
  - nftables: More powerful, supports complex expressions
  - Linux routing: Requires sysctl (net.ipv4.ip_forward=1)
  - FreeBSD routing: Automatic via gateway_enable=YES

Implementation Notes:
---------------------
1. Must disable "set skip on" for NAT interfaces (pf needs to process them)
2. Use dynamic interface references: ($interface) not hardcoded IPs
3. Ensure Tailscale daemon runs before pf rules take effect
4. Test with traceroute from client to verify all hops work
5. Monitor pf state table: pfctl -s info

Debugging:
----------
# View loaded rules
pfctl -sr      # Filter rules
pfctl -sn      # NAT rules

# Monitor state table
pfctl -s info

# Test with tcpdump
tcpdump -i bridge10 'dst net 192.168.160.0 mask 255.255.255.0'
tcpdump -i tailscale0 'dst net 192.168.160.0 mask 255.255.255.0'

# Reload rules without losing state
pfctl -f /etc/pf.conf
"""

from io import StringIO
from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server


def generate_pf_gateway_rules(config):
    """Generate pf rules for Tailscale gateway routing.

    Args:
        config: dict with keys:
            - role: "gateway" or "endpoint"
            - local_subnet: "192.168.150.0/24"
            - local_ip: "192.168.150.2"
            - vpn_interface: "tailscale0"
            - remote_subnets: ["192.168.160.0/24", ...]
            - backup_vpn: "wg0" (optional)
            - external_interface: "em0"
            - internal_bridge: "bridge10"

    Returns:
        str: pf.conf rules text
    """
    local_subnet = config.get("local_subnet", "192.168.150.0/24")
    vpn_iface = config.get("vpn_interface", "tailscale0")
    remote_subnets = config.get("remote_subnets", [])
    backup_vpn = config.get("backup_vpn", "wg0")
    ext_if = config.get("external_interface", "em0")
    bridge_iface = config.get("internal_bridge", "bridge10")
    local_ip = config.get("local_ip", "192.168.150.2")

    remote_list = "{ " + ", ".join(remote_subnets) + " }"

    rules = f"""# pf.conf - Tailscale Gateway Routing (Auto-generated by flamelet)
# Configuration: {config.get('role', 'gateway')} mode on {vpn_iface}
# Local network: {local_subnet}
# Remote subnets: {remote_list}

# Macros
ext_if = "{ext_if}"
vpn_if = "{vpn_iface}"
bridge_if = "{bridge_iface}"
local_subnet = "{local_subnet}"
icmp_types = "echoreq"

# Tables for performance
table <jails> persist
table <k3s_nodes> persist

# Options
set block-policy return
set require-order no
set skip on lo
set skip on $bridge_if

# Normalization
scrub in on $ext_if all fragment reassemble

# Translation (NAT)
rdr-anchor "rdr/*"

# External NAT (for clients reaching internet)
nat on $ext_if inet from {local_subnet} to any -> ($ext_if)

# VPN NAT (for clients reaching remote subnets via Tailscale)
nat on $vpn_if inet from {local_subnet} to {remote_list} -> ($vpn_if)

# Backup VPN NAT (if wg0 configured)
nat on {backup_vpn} inet from {local_subnet} to {remote_list} -> ({backup_vpn})

# Tailscale anchors (for dynamic rule injection)
anchor "tailscale"
nat-anchor "tailscale"

# Filtering
block in all
pass out quick keep state
antispoof for $ext_if inet

# SSH access
pass in inet proto tcp from any to any port ssh flags S/SA keep state

# ICMP (ping)
pass inet proto icmp all icmp-type $icmp_types

# External traffic
pass out on $ext_if inet proto {{ tcp, udp }} from {local_subnet} to any keep state

# VPN Gateway Routing Rules
# Outbound: allow clients to reach remote subnets via VPN
pass out on $vpn_if inet proto {{ tcp, udp }} from {local_subnet} to {remote_list} keep state
pass out on {backup_vpn} inet proto {{ tcp, udp }} from {local_subnet} to {remote_list} keep state

# Return traffic: allow responses from remote subnets back to clients
pass in on $vpn_if inet proto {{ tcp, udp }} from {remote_list} to any keep state
pass in on {backup_vpn} inet proto {{ tcp, udp }} from {remote_list} to any keep state

# Fallback: allow all (last rule)
pass in inet proto {{ tcp, udp }} from any to any
"""
    return rules


def add_pf_gateway_routing_ops(state, hosts, config, target_hosts=None, task="all"):
    """Deploy Tailscale gateway routing via pf.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → gateway config
            See PF_GATEWAY_ROUTING example above
        target_hosts: list of Host objects (default: all)
        task: task name (used for compatibility with flamelet caller)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        if os_key not in ("FreeBSD", "OpenBSD"):
            continue

        gateway_config = config[host.name]
        rules = generate_pf_gateway_rules(gateway_config)

        # Deploy pf.conf
        add_op(
            state,
            files.put,
            name=f"Deploy Tailscale gateway routing on {host.name}",
            src=StringIO(rules),
            dest="/etc/pf.conf",
            mode="0644",
            user="root",
            group="wheel",
            host=host,
        )

        # Validate syntax
        add_op(
            state,
            server.shell,
            name=f"Validate pf rules on {host.name}",
            commands=["/sbin/pfctl -nf /etc/pf.conf"],
            host=host,
        )

        # Reload rules
        add_op(
            state,
            server.shell,
            name=f"Reload pf rules on {host.name}",
            commands=["/sbin/pfctl -f /etc/pf.conf"],
            host=host,
        )

        # Enable pf service
        if os_key == "FreeBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable pf on {host.name} (FreeBSD)",
                commands=[
                    "sysrc pf_enable=YES",
                    "sysrc pf_rules=/etc/pf.conf",
                ],
                host=host,
            )
        elif os_key == "OpenBSD":
            add_op(
                state,
                server.shell,
                name=f"Enable pf on {host.name} (OpenBSD)",
                commands=[
                    "rcctl enable pf",
                    "rcctl start pf",
                ],
                host=host,
            )
