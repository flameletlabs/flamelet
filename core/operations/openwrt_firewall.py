"""OpenWrt firewall rules for Tailscale forwarding on GL.iNet devices."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server


def add_openwrt_firewall_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure persistent firewall rules on OpenWrt devices for Tailscale.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → firewall config
            {
                "uplink-2.work": {
                    "enable_tailscale_forwarding": True,  # Enable LAN ↔ Tailscale forwarding
                    "tailscale_interface": "tailscale0",   # Tailscale interface name
                    "lan_zone": "br-lan",                   # LAN bridge interface
                    "routing_table": 52,                    # Tailscale policy routing table
                    "policy_routing_rules": [               # Optional: additional routing rules
                        {"from": "192.168.80.0/24", "table": 52, "priority": 32765}
                    ],
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "openwrt_firewall" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        fw_config = config[host.name]

        if fw_config.get("enable_tailscale_forwarding"):
            _add_tailscale_forwarding(state, host, fw_config)

        if fw_config.get("policy_routing_rules"):
            _add_policy_routing(state, host, fw_config)


def _add_tailscale_forwarding(state, host, config):
    """Create startup script for persistent Tailscale firewall forwarding on OpenWrt."""

    ts_interface = config.get("tailscale_interface", "tailscale0")
    lan_zone = config.get("lan_zone", "br-lan")

    # Create init.d script for persistent firewall rules (using shell heredoc - no SFTP needed)
    init_script_create = f"""cat > /etc/init.d/tailscale-firewall << 'EOFSCRIPT'
#!/bin/sh /etc/rc.common

START=90  # Run after firewall (which is START=85)
STOP=10

start() {{
	# Wait for firewall to be fully initialized
	sleep 2

	# Add nftables rules for Tailscale forwarding
	nft add rule inet fw4 forward_lan 'iifname "{lan_zone}" oifname "{ts_interface}" counter accept comment "LAN to Tailscale"' 2>/dev/null || true
	nft add rule inet fw4 forward_lan 'iifname "{ts_interface}" oifname "{lan_zone}" counter accept comment "Tailscale to LAN"' 2>/dev/null || true

	# Masquerade Tailscale traffic
	iptables -t nat -I POSTROUTING -o {ts_interface} -j MASQUERADE 2>/dev/null || true

	# Allow ICMP through firewall
	iptables -I FORWARD -p icmp -j ACCEPT 2>/dev/null || true

	echo "$(date): Tailscale firewall rules loaded" >> /var/log/tailscale-fw.log
}}

stop() {{
	# Rules will be cleaned up on firewall restart
	true
}}
EOFSCRIPT
chmod 755 /etc/init.d/tailscale-firewall
"""

    # Deploy init.d script via shell command (SFTP not available on OpenWrt)
    add_op(
        state,
        server.shell,
        name=f"Deploy Tailscale firewall startup script on {host.name}",
        commands=[init_script_create],
        host=host,
    )

    # Enable service to start on boot
    add_op(
        state,
        server.shell,
        name=f"Enable tailscale-firewall service on {host.name}",
        commands=["/etc/init.d/tailscale-firewall enable"],
        host=host,
    )

    # Start the service
    add_op(
        state,
        server.shell,
        name=f"Start tailscale-firewall service on {host.name}",
        commands=["/etc/init.d/tailscale-firewall start"],
        host=host,
    )

    # Verify rules are applied
    add_op(
        state,
        server.shell,
        name=f"Verify Tailscale firewall rules on {host.name}",
        commands=["nft list chain inet fw4 forward_lan | grep -i tailscale || echo 'Rules pending'"],
        host=host,
    )


def _add_policy_routing(state, host, config):
    """Configure policy-based routing rules on OpenWrt."""

    rules = config.get("policy_routing_rules", [])

    # Create startup script for routing rules
    routing_script = """#!/bin/sh /etc/rc.common

START=85  # Run before tailscale-firewall

start() {
	# Applied routing rules from policy_routing_rules
"""

    for rule in rules:
        from_net = rule.get("from")
        table = rule.get("table", 52)
        priority = rule.get("priority", 1000)

        routing_script += f'\tif ! ip rule show | grep -q "from {from_net}"; then\n'
        routing_script += f'\t\tip rule add from {from_net} lookup {table} priority {priority}\n'
        routing_script += '\tfi\n'

    routing_script += """\techo "$(date): Policy routing rules loaded" >> /var/log/tailscale-routing.log
}

stop() {
	# Rules cleaned up by system
	true
}
"""

    # Deploy routing script via shell (SFTP not available on OpenWrt)
    routing_script_create = f"""cat > /etc/init.d/tailscale-routing << 'EOFSCRIPT'
{routing_script}
EOFSCRIPT
chmod 755 /etc/init.d/tailscale-routing
"""

    add_op(
        state,
        server.shell,
        name=f"Deploy policy routing script on {host.name}",
        commands=[routing_script_create],
        host=host,
    )

    # Enable service
    add_op(
        state,
        server.shell,
        name=f"Enable tailscale-routing service on {host.name}",
        commands=["/etc/init.d/tailscale-routing enable"],
        host=host,
    )

    # Start the service
    add_op(
        state,
        server.shell,
        name=f"Start tailscale-routing service on {host.name}",
        commands=["/etc/init.d/tailscale-routing start"],
        host=host,
    )
