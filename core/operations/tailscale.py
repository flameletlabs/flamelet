"""Tailscale VPN mesh deployment and configuration."""

from pyinfra.api.operation import add_op
from pyinfra.facts.server import Kernel
from pyinfra.operations import apt, pkg, server


def add_tailscale_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure Tailscale VPN mesh on hosts.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname → Tailscale config
            {
                "host.example.com": {
                    "hostname": "host-mesh-name",          # Tailscale device hostname
                    "advertise_routes": ["192.168.0.0/24"], # Subnets to advertise
                    "accept_routes": True,                  # Accept routes from other nodes
                    "auth_key": "tskey-auth-...",          # Pre-auth key (optional, uses default)
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "tailscale" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    # Default pre-auth key for mesh deployment
    DEFAULT_AUTH_KEY = "tskey-auth-kMFTtcVone11CNTRL-fHKjNMbNbK3kGVL6fb3WJ3atngBSJshM"

    for host in targets:
        if host.name not in config:
            continue

        os_key = host.get_fact(Kernel)
        ts_config = config[host.name]

        # Extract configuration
        hostname = ts_config.get("hostname", host.name)
        advertise_routes = ts_config.get("advertise_routes", [])
        accept_routes = ts_config.get("accept_routes", True)
        auth_key = ts_config.get("auth_key", DEFAULT_AUTH_KEY)

        if os_key == "FreeBSD":
            _add_tailscale_freebsd(state, host, hostname, advertise_routes, accept_routes, auth_key)
        elif os_key == "OpenBSD":
            _add_tailscale_openbsd(state, host, hostname, advertise_routes, accept_routes, auth_key)
        elif os_key == "Linux":
            _add_tailscale_linux(state, host, hostname, advertise_routes, accept_routes, auth_key)


def _add_tailscale_freebsd(state, host, hostname, advertise_routes, accept_routes, auth_key):
    """Configure Tailscale on FreeBSD."""

    # Install tailscale package
    add_op(
        state,
        pkg.packages,
        name=f"Install tailscale on {host.name}",
        packages=["tailscale"],
        host=host,
    )

    # Enable tailscaled service
    add_op(
        state,
        server.shell,
        name=f"Enable tailscaled on {host.name}",
        commands=["sysrc tailscaled_enable=YES"],
        host=host,
    )

    # Start tailscaled service
    add_op(
        state,
        server.shell,
        name=f"Start tailscaled on {host.name}",
        commands=["service tailscaled start"],
        host=host,
    )

    # Wait for daemon to be ready
    add_op(
        state,
        server.shell,
        name=f"Wait for tailscaled to be ready on {host.name}",
        commands=["sleep 2"],
        host=host,
    )

    # Authenticate with pre-auth key
    auth_cmd = f"tailscale up --auth-key={auth_key} --hostname={hostname}"
    if accept_routes:
        auth_cmd += " --accept-routes"

    add_op(
        state,
        server.shell,
        name=f"Authenticate Tailscale on {host.name}",
        commands=[auth_cmd],
        host=host,
    )

    # Advertise routes (if any specified)
    if advertise_routes:
        routes_str = ",".join(advertise_routes)
        add_op(
            state,
            server.shell,
            name=f"Advertise routes on {host.name}",
            commands=[f"tailscale up --advertise-routes={routes_str}"],
            host=host,
        )

    # Verify connection
    add_op(
        state,
        server.shell,
        name=f"Verify Tailscale status on {host.name}",
        commands=["tailscale status"],
        host=host,
    )


def _add_tailscale_openbsd(state, host, hostname, advertise_routes, accept_routes, auth_key):
    """Configure Tailscale on OpenBSD."""

    # Install tailscale package
    add_op(
        state,
        server.shell,
        name=f"Install tailscale on {host.name}",
        commands=["pkg_add -I tailscale"],
        host=host,
    )

    # Enable tailscaled service
    add_op(
        state,
        server.shell,
        name=f"Enable tailscaled on {host.name}",
        commands=["rcctl enable tailscaled"],
        host=host,
    )

    # Start tailscaled service
    add_op(
        state,
        server.shell,
        name=f"Start tailscaled on {host.name}",
        commands=["rcctl start tailscaled"],
        host=host,
    )

    # Wait for daemon to be ready
    add_op(
        state,
        server.shell,
        name=f"Wait for tailscaled to be ready on {host.name}",
        commands=["sleep 2"],
        host=host,
    )

    # Authenticate with pre-auth key
    auth_cmd = f"tailscale up --auth-key={auth_key} --hostname={hostname}"
    if accept_routes:
        auth_cmd += " --accept-routes"

    add_op(
        state,
        server.shell,
        name=f"Authenticate Tailscale on {host.name}",
        commands=[auth_cmd],
        host=host,
    )

    # Advertise routes (if any specified)
    if advertise_routes:
        routes_str = ",".join(advertise_routes)
        add_op(
            state,
            server.shell,
            name=f"Advertise routes on {host.name}",
            commands=[f"tailscale up --advertise-routes={routes_str}"],
            host=host,
        )

    # Verify connection
    add_op(
        state,
        server.shell,
        name=f"Verify Tailscale status on {host.name}",
        commands=["tailscale status"],
        host=host,
    )


def _add_tailscale_linux(state, host, hostname, advertise_routes, accept_routes, auth_key):
    """Configure Tailscale on Linux (Debian/Alpine - PiKVM)."""

    # For PiKVM (read-only filesystem): enable write mode first
    add_op(
        state,
        server.shell,
        name=f"Enable write mode on {host.name}",
        commands=["rw"],
        host=host,
    )

    # Install tailscale package
    add_op(
        state,
        apt.packages,
        name=f"Install tailscale on {host.name}",
        packages=["tailscale"],
        host=host,
    )

    # Enable tailscaled service (systemd)
    add_op(
        state,
        server.shell,
        name=f"Enable tailscaled on {host.name}",
        commands=["systemctl enable tailscaled"],
        host=host,
    )

    # Start tailscaled service
    add_op(
        state,
        server.shell,
        name=f"Start tailscaled on {host.name}",
        commands=["systemctl start tailscaled"],
        host=host,
    )

    # Wait for daemon to be ready
    add_op(
        state,
        server.shell,
        name=f"Wait for tailscaled to be ready on {host.name}",
        commands=["sleep 2"],
        host=host,
    )

    # Authenticate with pre-auth key
    auth_cmd = f"tailscale up --auth-key={auth_key} --hostname={hostname}"
    if accept_routes:
        auth_cmd += " --accept-routes"

    add_op(
        state,
        server.shell,
        name=f"Authenticate Tailscale on {host.name}",
        commands=[auth_cmd],
        host=host,
    )

    # Advertise routes (if any specified)
    if advertise_routes:
        routes_str = ",".join(advertise_routes)
        add_op(
            state,
            server.shell,
            name=f"Advertise routes on {host.name}",
            commands=[f"tailscale up --advertise-routes={routes_str}"],
            host=host,
        )

    # Return to read-only mode (for PiKVM)
    add_op(
        state,
        server.shell,
        name=f"Return to read-only mode on {host.name}",
        commands=["ro"],
        host=host,
    )

    # Verify connection
    add_op(
        state,
        server.shell,
        name=f"Verify Tailscale status on {host.name}",
        commands=["tailscale status"],
        host=host,
    )
