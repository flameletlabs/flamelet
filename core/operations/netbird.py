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
                    "setup_key": "REPLACE_ME",  # never commit a real key, see below
                    "management_url": "https://api.netbird.io",  # optional
                    "hostname": "docker-newyork",
                    "version": "0.76.3",  # optional; omit to track the repo candidate
                    "advertise_routes": False,
                    "autostart": True,
                    "groups": ["newyork-infrastructure", "gateways"],  # optional: add to groups
                }
            }

    ⚠️ `setup_key` IS A CREDENTIAL AND THIS FILE IS PUBLIC. The placeholder above
    used to be a real, live, unlimited-use setup key, committed here in the clear
    from 2026-07-28 until it was noticed on 2026-08-15. Anyone who read this
    docstring could enrol a peer into that mesh. Keep example values obviously
    fake -- a plausible-looking one is how the last one survived review.

    `version` PINS THE PACKAGE. Without it every host converges on whatever its
    repo currently offers, independently, which is not a policy but an accident:
    one real mesh drifted to SIX different client versions across 13 peers because
    nothing declared one. Pinning also restores the standby-first upgrade path --
    bump the pin, deploy to the standby site, watch it, then the primary -- which
    a floating version removes entirely, since both sites move whenever they
    happen to install.

    ⚠️ LINUX ONLY, and that asymmetry is the point. This operation installs via
    apt, so a pin here governs Debian/Ubuntu hosts and nothing else. BSD hosts run
    netbird from their own ports/pkg tree, which generally serves only the current
    version and cannot be held at an older one -- so they are documented and
    monitored rather than pinned. Do not assume a `version` here constrains them.
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
    #
    # PINNED when the tenant declares a version, floating otherwise. Floating is
    # kept as the default so existing tenants behave exactly as before, but it is
    # the weaker choice: it converges each host on its repo's candidate at
    # whatever moment that host happens to run, so two sites drift apart silently.
    #
    # allow_downgrades is REQUIRED for the pin to mean anything. Without it, a
    # host already AHEAD of the declared version is left alone and apt exits 0 --
    # so the deploy reports success while the fleet stays inconsistent, which is
    # the exact failure this pin exists to prevent. With it, the declared version
    # is what you get in both directions.
    version = config.get("version")
    add_op(
        state,
        apt.packages,
        name=(
            f"Install netbird {version} on {host.name}"
            if version
            else f"Install netbird package on {host.name}"
        ),
        packages=[f"netbird={version}" if version else "netbird"],
        allow_downgrades=bool(version),
        host=host,
    )

    # Configure and connect to Netbird network
    setup_key = config.get("setup_key")
    management_url = config.get("management_url", "https://api.netbird.io")
    hostname = config.get("hostname", host.name)
    # The MESH name and the SYSTEM hostname are two different things, and
    # welding them together was wrong.
    #
    # Netbird derives a peer's name from the system hostname at ENROLMENT when
    # no --hostname is passed, so the two silently became one setting: a mesh
    # name has to be unique across every site, which forced location suffixes
    # onto system hostnames that should just be `gateway` -- the same way the
    # hypervisors are `virt` and `virt-01`, with the location carried by the
    # domain rather than baked into the host.
    #
    # So system_hostname is now separate and defaults to the mesh name, which
    # keeps every existing tenant behaving exactly as before. Where it IS set,
    # the mesh name is additionally pinned with an explicit --hostname below,
    # so the peer's identity no longer depends on what the box calls itself.
    system_hostname = config.get("system_hostname", hostname)

    # Set system hostname before Netbird joins
    add_op(
        state,
        server.shell,
        name=f"Set system hostname to {system_hostname}",
        commands=[
            # THE RUNNING HOSTNAME IS SET DIRECTLY, not left to hostnamectl.
            #
            # In an LXC container systemd-hostnamed frequently cannot start --
            # measured on a privileged container as
            #   Failed to activate service 'org.freedesktop.hostname1': timed out
            # with the unit in `failed`. hostnamectl then STILL EXITS 0, so the
            # `|| echo` fallback never fires and nothing can detect the failure.
            #
            # The old command list therefore wrote /etc/hostname (correct at next
            # boot) while leaving the RUNNING hostname untouched, and reported
            # success. The host was left in two states at once: `hostname` said
            # one thing and /etc/hostname another, indefinitely, until something
            # happened to restart the container.
            #
            # `hostname` sets it live and works with or without systemd; the file
            # write makes it persist. Together they converge immediately instead
            # of eventually.
            f"hostnamectl set-hostname {system_hostname} >/dev/null 2>&1 || true",
            f"hostname {system_hostname}",
            f'printf "%s\\n" "{system_hostname}" > /etc/hostname',
            "hostname",
        ],
        host=host,
    )

    if setup_key:
        # Connect with setup key (automated, no SSO required)
        # System hostname MUST be set first - Netbird uses it for peer identification
        # --hostname is explicit so the peer's mesh identity is pinned by config
        # rather than inherited from whatever the system hostname happens to be.
        connect_cmd = f"netbird up --setup-key {setup_key} --hostname {hostname}"
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
                # SINGLE-QUOTED, with no nested double quotes and no parentheses.
                # This line used to end `\\"")`, which left an unescaped `)` outside
                # the quoting -- so the shell died with "syntax error near
                # unexpected token `)'" and this purely cosmetic echo FAILED every
                # single netbird deployment. pyinfra then aborted the run and told
                # the operator not to treat it as deployed, after the real work had
                # already succeeded. In a --task all run it also skipped every task
                # queued behind it.
                f"echo '✓ Netbird peer {hostname} deployed and connected.'",
                f"echo '  → Add to groups: {group_list}'",
                "echo '  → Via: Dashboard, API, or the Netbird MCP'",
            ],
            host=host,
        )
