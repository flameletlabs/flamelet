"""WireGuard VPN configuration and management."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import files, server


def add_wireguard_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure WireGuard VPN on hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → WireGuard config
            {
                "vpn.example.com": {
                    "interfaces": {
                        "wg0": {
                            "address": "10.0.0.2/24",
                            "port": 51820,
                            "private_key": "OMk2zN8aA5bB6cC7dD8eE9fF0gG1hH2i=",
                            "peers": [
                                {
                                    "pubkey": "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpP=",
                                    "allowed_ips": ["10.0.0.0/24"],
                                    "endpoint": "vpn-gateway.example.com:51820",
                                    "keepalive": 25,
                                    "preshared_key": "xXyYzZaAbBcCdDeEfFgGhHiIjJkKlMmN="  # optional
                                }
                            ]
                        }
                    }
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "wireguard" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        wg_config = config[host.name]
        interfaces = wg_config.get("interfaces", {})

        for iface_name, iface_config in interfaces.items():
            if os_key == "FreeBSD":
                _add_wireguard_freebsd(state, host, iface_name, iface_config)
            elif os_key == "OpenBSD":
                _add_wireguard_openbsd(state, host, iface_name, iface_config)
            elif os_key == "Linux":
                _add_wireguard_linux(state, host, iface_name, iface_config)


def _add_wireguard_freebsd(state, host, iface_name, config):
    """Configure WireGuard on FreeBSD via /usr/local/etc/wireguard/<iface>.conf"""
    content = _generate_wireguard_ini(config)

    # Write wg config file
    add_op(
        state,
        files.put,
        name=f"Deploy WireGuard config {iface_name} on {host.name}",
        src=StringIO(content),
        dest=f"/usr/local/etc/wireguard/{iface_name}.conf",
        mode="0640",
        user="root",
        group="wheel",
        host=host,
    )

    # Enable and configure sysrc
    add_op(
        state,
        server.shell,
        name=f"Enable WireGuard {iface_name} on {host.name}",
        commands=[
            "sysrc wireguard_enable=YES",
            f"sysrc -a wireguard_interfaces+={iface_name}",
            "service wireguard restart || true",
        ],
        host=host,
    )

    # Add routes for AllowedIPs (FreeBSD doesn't auto-create them like Linux does)
    peers = config.get("peers", [])
    route_commands = []
    for peer in peers:
        for ip in peer.get("allowed_ips", []):
            route_commands.append(f"route add -inet {ip} -link -iface {iface_name} || true")

    if route_commands:
        add_op(
            state,
            server.shell,
            name=f"Add routes for WireGuard {iface_name} on {host.name}",
            commands=route_commands,
            host=host,
        )


def _add_wireguard_openbsd(state, host, iface_name, config):
    """Configure WireGuard on OpenBSD via /etc/hostname.<iface>"""
    content = _generate_wireguard_openbsd(config, iface_name)

    # Write OpenBSD hostname.<iface> file
    add_op(
        state,
        files.put,
        name=f"Deploy WireGuard config {iface_name} on {host.name}",
        src=StringIO(content),
        dest=f"/etc/hostname.{iface_name}",
        mode="0640",
        user="root",
        group="wheel",
        host=host,
    )

    # Bring up interface
    add_op(
        state,
        server.shell,
        name=f"Activate WireGuard {iface_name} on {host.name}",
        commands=[f"sh /etc/netstart {iface_name}"],
        host=host,
    )


def _add_wireguard_linux(state, host, iface_name, config):
    """Configure WireGuard on Linux via /etc/wireguard/<iface>.conf + wg-quick."""
    content = _generate_wireguard_ini(config)

    add_op(
        state,
        files.put,
        name=f"Deploy WireGuard config {iface_name} on {host.name}",
        src=StringIO(content),
        dest=f"/etc/wireguard/{iface_name}.conf",
        mode="0640",
        user="root",
        group="root",
        host=host,
    )

    add_op(
        state,
        server.shell,
        name=f"Enable WireGuard {iface_name} on {host.name}",
        commands=[
            f"systemctl enable wg-quick@{iface_name}",
            f"systemctl restart wg-quick@{iface_name} || true",
        ],
        host=host,
    )


def _generate_wg_freebsd_config(config):
    """Generate WireGuard FreeBSD config."""
    return _generate_wireguard_ini(config)


def _generate_wireguard_ini(config):
    """Generate WireGuard INI format config (FreeBSD style)."""
    lines = ["[Interface]"]
    lines.append(f"Address = {config.get('address', '')}")
    lines.append(f"ListenPort = {config.get('port', 51820)}")
    lines.append(f"PrivateKey = {config.get('private_key', '')}")

    peers = config.get("peers", [])
    for peer in peers:
        lines.append("")
        lines.append("[Peer]")
        lines.append(f"PublicKey = {peer.get('pubkey', '')}")
        if "preshared_key" in peer:
            lines.append(f"PresharedKey = {peer['preshared_key']}")
        allowed_ips = peer.get("allowed_ips", [])
        lines.append(f"AllowedIPs = {', '.join(allowed_ips)}")
        if "endpoint" in peer:
            lines.append(f"Endpoint = {peer['endpoint']}")
        if "keepalive" in peer:
            lines.append(f"PersistentKeepalive = {peer['keepalive']}")

    return "\n".join(lines)


def _generate_wireguard_openbsd(config, iface_name="wg0"):
    """Generate WireGuard config for OpenBSD /etc/hostname.<iface> format."""
    lines = []
    address = config.get("address", "")
    port = config.get("port", 51820)
    privkey = config.get("private_key", "")

    # OpenBSD ifconfig syntax: inet address wgport port wgkey privkey
    lines.append(f"{address} wgport {port} wgkey {privkey}")

    # Add peers
    peers = config.get("peers", [])
    for peer in peers:
        pubkey = peer.get("pubkey", "")
        lines.append("")
        lines.append(f"wgpeer {pubkey} \\")

        # Allowed IPs
        allowed_ips = peer.get("allowed_ips", [])
        for ip in allowed_ips:
            lines.append(f"  wgaip {ip} \\")

        # Endpoint
        if "endpoint" in peer:
            lines.append(f"  wgendpoint {peer['endpoint']} \\")

        # Keepalive
        if "keepalive" in peer:
            lines.append(f"  wgpka {peer['keepalive']} \\")

        # Remove trailing backslash from last line
        if lines[-1].endswith(" \\"):
            lines[-1] = lines[-1][:-2]

    # Add routes for allowed IPs
    for peer in peers:
        for ip in peer.get("allowed_ips", []):
            lines.append(f"!/sbin/route add -inet {ip} -link -iface {iface_name}")

    return "\n".join(lines)
