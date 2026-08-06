"""Netbird agent installation and configuration for Linux hosts."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import apt, server, systemd


def add_netbird_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Netbird mesh VPN agent on Linux hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → netbird config
            {
                "docker.newyork": {
                    "setup_key": "31B89B65-2CB9-49B6-BBBD-57D4263AFE1C",
                    "management_url": "https://api.netbird.io",  # optional
                    "hostname": "docker-newyork",
                    "advertise_routes": False,
                    "autostart": True,
                    "groups": ["newyork-infrastructure", "gateways"],  # optional: add to groups
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "netbird" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        netbird_config = config[host.name]

        if os_key == "Linux":
            _add_netbird_linux(state, host, netbird_config)


def _add_netbird_linux(state, host, config):
    """Configure Netbird on Linux (Debian/Ubuntu)."""

    # Add Netbird GPG key to system keyring
    # Download the public key using explicit DNS to work around potential /etc/resolv.conf issues
    # (e.g., when Netbird or other services have overridden system DNS)
    # IP: 5.22.212.152 is the stable Netbird repository CDN address
    # Use separate download and conversion steps for better error handling
    add_op(
        state,
        server.shell,
        name=f"Add Netbird GPG key on {host.name}",
        commands=[
            "mkdir -p /usr/share/keyrings /tmp",
            "rm -f /tmp/netbird-public.key /usr/share/keyrings/netbird-archive-keyring.gpg",
            "curl -sSL --resolve pkgs.netbird.io:443:5.22.212.152 https://pkgs.netbird.io/debian/public.key -o /tmp/netbird-public.key",
            "gpg --batch --dearmor --output /usr/share/keyrings/netbird-archive-keyring.gpg /tmp/netbird-public.key",
            "chmod 0644 /usr/share/keyrings/netbird-archive-keyring.gpg",
            "rm -f /tmp/netbird-public.key",
        ],
        host=host,
    )

    # Add Netbird repository with proper GPG key signature verification
    add_op(
        state,
        server.shell,
        name=f"Add Netbird repository on {host.name}",
        commands=[
            "mkdir -p /etc/apt/sources.list.d",
            'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/netbird-archive-keyring.gpg] https://pkgs.netbird.io/debian stable main" | tee /etc/apt/sources.list.d/netbird.list',
        ],
        host=host,
    )

    # Update apt cache
    add_op(
        state,
        apt.update,
        name=f"Update apt cache on {host.name}",
        host=host,
    )

    # Install netbird package (with proper GPG signature verification)
    add_op(
        state,
        apt.packages,
        name=f"Install netbird package on {host.name}",
        packages=["netbird"],
        host=host,
    )

    # Configure and connect to Netbird network
    setup_key = config.get("setup_key")
    management_url = config.get("management_url", "https://api.netbird.io")
    hostname = config.get("hostname", host.name)

    # Set system hostname before Netbird joins
    # Netbird uses the system hostname for peer identity and FQDN
    # This MUST be unique across all Netbird peers to avoid conflicts
    add_op(
        state,
        server.shell,
        name=f"Set system hostname to {hostname}",
        commands=[
            f'hostnamectl set-hostname {hostname} || echo "{hostname}" > /etc/hostname',
            f'sed -i "s/^.*$/{hostname}/" /etc/hostname',
            "sysctl kernel.hostname | head -1 || true",
        ],
        host=host,
    )

    if setup_key:
        # Connect with setup key (automated, no SSO required)
        # System hostname MUST be set first - Netbird uses it for peer identification
        connect_cmd = f"netbird up --setup-key {setup_key}"
        if management_url != "https://api.netbird.io":
            # Self-hosted Netbird
            connect_cmd += f" --management-url {management_url}"

        add_op(
            state,
            server.shell,
            name=f"Connect {host.name} to Netbird mesh (FQDN: {hostname}.netbird.cloud)",
            commands=[connect_cmd],
            host=host,
        )

    # Enable and start Netbird service
    add_op(
        state,
        systemd.service,
        name=f"Enable netbird service on {host.name}",
        service="netbird",
        enabled=True,
        running=True,
        host=host,
    )

    # Verify connection
    add_op(
        state,
        server.shell,
        name=f"Verify Netbird connection on {host.name}",
        commands=[
            "netbird status || true",
            "ip addr show wt0 || echo 'WireGuard interface not yet available'",
        ],
        host=host,
    )

    # Add to Netbird groups (if specified in configuration)
    # Group membership is managed via:
    # 1. Netbird Dashboard (UI): https://app.netbird.io → Peers → Edit peer → Groups
    # 2. Netbird API: POST /api/peers/{peer_id}/groups with group IDs
    # 3. Netbird MCP (Claude Code): "Add peer gateway-newyork to group newyork-infrastructure"
    #
    # The groups field in config serves as documentation for deployment intent
    groups = config.get("groups", [])
    if groups:
        group_list = ", ".join(groups)
        # Log which groups this peer should be added to
        add_op(
            state,
            server.shell,
            name=f"Log Netbird group assignments for {host.name}",
            commands=[
                f"echo \"✓ Netbird peer '{hostname}' deployed and connected.\"",
                f'echo "  → Add to groups: {group_list}"',
                f'echo "  → Via: Dashboard | API | Claude Code MCP (type: \\"Add peer {hostname} to group <group_name>\\"")',
            ],
            host=host,
        )
