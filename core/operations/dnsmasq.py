"""dnsmasq DNS/DHCP server configuration and management."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import apt, pkg, server


# OS-specific configuration defaults
_OS_DEFAULTS = {
    "FreeBSD": {
        "conf_path": "/usr/local/etc/dnsmasq.conf",
        "pid_path": "/var/run/dnsmasq.pid",
        "lease_path": "/var/db/dnsmasq.leases",
        "service_name": "dnsmasq",
    },
    "Linux": {
        "conf_path": "/etc/dnsmasq.conf",
        "pid_path": "/var/run/dnsmasq.pid",
        "lease_path": "/var/lib/dnsmasq/dnsmasq.leases",
        "service_name": "dnsmasq",
    },
}


def add_dnsmasq_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure dnsmasq DNS/DHCP server on FreeBSD and Linux hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → dnsmasq config
            {
                "virt-01.baar": {
                    "listen": ["192.168.160.1", "127.0.0.1"],
                    "servers": ["1.1.1.1", "8.8.8.8"],
                    "address": ["/postgresql.baar.home/192.168.160.100", ...],
                    "server": ["/home./192.168.150.2", "/pangea./192.168.180.50"],
                    "dhcp_update": {"enabled": True, "allow_update": [...]},
                    "options": {"cache_size": "10000", "log_queries": False, ...}
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "dnsmasq" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        dnsmasq_config = config[host.name]

        if os_key == "FreeBSD":
            _add_dnsmasq_freebsd(state, host, dnsmasq_config)
        elif os_key == "Linux":
            _add_dnsmasq_linux(state, host, dnsmasq_config)


def _add_dnsmasq_freebsd(state, host, config):
    """Configure dnsmasq on FreeBSD."""
    os_defaults = _OS_DEFAULTS["FreeBSD"]

    # Install package
    add_op(
        state,
        pkg.packages,
        name=f"Install dnsmasq on {host.name}",
        packages=["dnsmasq"],
        host=host,
    )

    # Generate and deploy config
    conf_content = _generate_dnsmasq_conf(config, os_defaults)
    heredoc_cmd = (
        f"cat > {os_defaults['conf_path']} << 'DNSMASQ_EOF'\n"
        f"{conf_content}\nDNSMASQ_EOF"
    )

    add_op(
        state,
        server.shell,
        name=f"Deploy dnsmasq config on {host.name}",
        commands=[heredoc_cmd],
        host=host,
    )

    # Set permissions
    add_op(
        state,
        server.shell,
        name=f"Set dnsmasq config permissions on {host.name}",
        commands=[f"chmod 0644 {os_defaults['conf_path']}"],
        host=host,
    )

    # Enable and start service
    add_op(
        state,
        server.shell,
        name=f"Enable dnsmasq on {host.name}",
        commands=[
            "sysrc dnsmasq_enable=YES",
            "service dnsmasq restart || true",
        ],
        host=host,
    )

    # Update resolv.conf to use local dnsmasq (for auto-DNS to work)
    add_op(
        state,
        server.shell,
        name=f"Configure resolver to use local dnsmasq on {host.name}",
        commands=[
            "echo 'nameserver 127.0.0.1' > /etc/resolv.conf",
            "grep -q 'nameserver 192.168' /etc/resolv.conf || echo 'nameserver 192.168.150.1' >> /etc/resolv.conf",
            "grep -q 'nameserver 1.1.1.1' /etc/resolv.conf || echo 'nameserver 1.1.1.1' >> /etc/resolv.conf",
        ],
        host=host,
    )


def _add_dnsmasq_linux(state, host, config):
    """Configure dnsmasq on Linux (Debian/Ubuntu/Alpine)."""
    os_defaults = _OS_DEFAULTS["Linux"]

    # Install package
    add_op(
        state,
        apt.packages,
        name=f"Install dnsmasq on {host.name}",
        packages=["dnsmasq"],
        host=host,
    )

    # Generate and deploy config
    conf_content = _generate_dnsmasq_conf(config, os_defaults)
    heredoc_cmd = (
        f"cat > {os_defaults['conf_path']} << 'DNSMASQ_EOF'\n"
        f"{conf_content}\nDNSMASQ_EOF"
    )

    add_op(
        state,
        server.shell,
        name=f"Deploy dnsmasq config on {host.name}",
        commands=[heredoc_cmd],
        host=host,
    )

    # Set permissions
    add_op(
        state,
        server.shell,
        name=f"Set dnsmasq config permissions on {host.name}",
        commands=[f"chmod 0644 {os_defaults['conf_path']}"],
        host=host,
    )

    # Enable and start service
    add_op(
        state,
        server.shell,
        name=f"Enable dnsmasq on {host.name}",
        commands=[
            "systemctl enable dnsmasq",
            "systemctl restart dnsmasq || true",
        ],
        host=host,
    )

    # Update resolv.conf to use local dnsmasq (for auto-DNS to work)
    add_op(
        state,
        server.shell,
        name=f"Configure resolver to use local dnsmasq on {host.name}",
        commands=[
            "echo 'nameserver 127.0.0.1' > /etc/resolv.conf",
            "echo 'nameserver 1.1.1.1' >> /etc/resolv.conf",
        ],
        host=host,
    )


def _generate_dnsmasq_conf(config, os_defaults):
    """Generate dnsmasq.conf file content.

    Args:
        config: dnsmasq configuration dict
        os_defaults: OS-specific defaults (paths, etc.)

    Returns:
        String containing dnsmasq.conf content
    """
    lines = [
        "# Generated by Flamelet dnsmasq operation",
        "# Configuration managed via: flamelet --task dnsmasq",
        "",
    ]

    # Listen addresses (required)
    listen_addrs = config.get("listen", ["127.0.0.1"])
    if listen_addrs:
        for addr in listen_addrs:
            lines.append(f"listen-address={addr}")
        lines.append("")

    # Interface binding (for DHCP broadcast - optional)
    interfaces = config.get("interface", [])
    if interfaces:
        if isinstance(interfaces, str):
            interfaces = [interfaces]
        for iface in interfaces:
            lines.append(f"interface={iface}")
        lines.append("")

    # Upstream DNS servers (required)
    servers = config.get("servers", [])
    if servers:
        for server_addr in servers:
            lines.append(f"server={server_addr}")
        lines.append("")

    # Static DNS records (A records)
    addresses = config.get("address", [])
    if addresses:
        for addr_record in addresses:
            lines.append(f"address={addr_record}")
        lines.append("")

    # Zone forwarding (for cross-location DNS)
    zone_servers = config.get("server", [])
    if zone_servers:
        for zone_server in zone_servers:
            lines.append(f"server={zone_server}")
        lines.append("")

    # RFC 2136 DNS UPDATE support (DHCP integration)
    dhcp_update = config.get("dhcp_update", {})
    if dhcp_update.get("enabled", False):
        lines.append("# RFC 2136 DNS UPDATE support")
        allow_update = dhcp_update.get("allow_update", ["127.0.0.1"])
        for update_addr in allow_update:
            lines.append(f"update-allowed={update_addr}")
        lines.append("")

    # Additional options
    options = config.get("options", {})
    if options:
        cache_size = options.get("cache_size", "10000")
        lines.append(f"cache-size={cache_size}")

        if options.get("log_queries", False):
            lines.append("log-queries")

        if options.get("log_dhcp", False):
            lines.append("log-dhcp")

        if options.get("dhcp_fqdn", False):
            lines.append("dhcp-fqdn")
            # dhcp-fqdn requires a default domain
            domain = options.get("domain", "local")
            lines.append(f"domain={domain}")

        if options.get("dhcp_authoritative", False):
            lines.append("dhcp-authoritative")

        lines.append("")

    # DHCP configuration (if specified)
    dhcp_config = config.get("dhcp")
    if dhcp_config:
        lines.append("# DHCP server configuration")

        # Support both single dict and list of dicts formats
        dhcp_subnets = dhcp_config if isinstance(dhcp_config, list) else [dhcp_config]

        for subnet in dhcp_subnets:
            # Format: dhcp-range=192.168.160.128,192.168.160.200,12h
            start = subnet.get("start")
            end = subnet.get("end")
            lease = subnet.get("lease", "12h")
            if start and end:
                lines.append(f"dhcp-range={start},{end},{lease}")

        # Global DHCP options (apply to all subnets)
        # Router option: use router from first subnet, or default to gateway
        router = None
        for subnet in dhcp_subnets:
            if "router" in subnet:
                router = subnet["router"]
                break
        if router:
            lines.append(f"dhcp-option=3,{router}")  # Router with IP
        else:
            lines.append("dhcp-option=3")  # Router (default)

        # DNS servers - check for per-subnet config first, otherwise use default
        dns_servers = None
        for subnet in dhcp_subnets:
            if "dns_servers" in subnet:
                dns_servers = subnet["dns_servers"]
                break

        if dns_servers:
            dns_list = ",".join(dns_servers)
            lines.append(f"dhcp-option=6,{dns_list}")
        else:
            lines.append("dhcp-option=6,1.1.1.1,8.8.8.8")  # Default: Cloudflare, Google

        # Lease file (global)
        lease_file = config.get("options", {}).get("lease_file", os_defaults["lease_path"])
        lines.append(f"dhcp-leasefile={lease_file}")

        lines.append("")

    return "\n".join(lines)
