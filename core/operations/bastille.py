"""FreeBSD Bastille jail operations."""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server


def _sysrc(jail, key, value):
    """Return a bastille sysrc command string."""
    return f'bastille sysrc {jail} {key}="{value}"'


def add_bastille_ops(state, hosts, config, target_hosts=None, task="all"):
    """Manage FreeBSD Bastille jails.

    Config attribute: BASTILLE (hostname-keyed)

    Each host entry has:
      release:      FreeBSD release to bootstrap (e.g. "14.3-RELEASE")
      bridge:       bridge interface for VNET jails (default: "bridge10")
      zfs_enable:   enable ZFS storage for bastille (default: True)
      zfs_zpool:    ZFS pool name (default: "zroot")
      jails:        list of jail definitions (see below)

    Jail definition:
      name:         jail name (required)
      release:      FreeBSD release (overrides host-level, required)
      ip:           static IP with prefix, e.g. "192.168.1.10/24"
                    use "0.0.0.0" for DHCP
      gateway:      default router for the jail
      bridge:       bridge interface (overrides host-level)
      thick:        use thick jail (default: True)
      static_mac:   use a stable MAC address (default: True)
      allow:        dict of jail allow.* flags, e.g. {"raw_sockets": 1}
      sysvipc:      enable SysV IPC (sysvmsg/sysvsem/sysvshm, default: False)
      packages:     list of packages to install inside the jail
      ssh:          enable sshd + copy authorized_keys (default: True)
      authorized_keys_src: path on host to copy authorized_keys from
                    (default: /root/.ssh/authorized_keys)
      autostart:    enable jail at boot (default: True)
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        spec = config[host.name]
        release = spec.get("release", "14.3-RELEASE")
        bridge = spec.get("bridge", "bridge10")
        zfs_enable = spec.get("zfs_enable", True)
        zfs_zpool = spec.get("zfs_zpool", "zroot")
        jails = spec.get("jails", [])

        # Enable bastille in rc.conf and configure ZFS
        rc_cmds = [
            "sysrc bastille_enable=YES",
            "sysrc bastille_rcorder=NO",
        ]
        if zfs_enable:
            rc_cmds += [
                f"sysrc -f /usr/local/etc/bastille/bastille.conf bastille_zfs_enable=YES",
                f"sysrc -f /usr/local/etc/bastille/bastille.conf bastille_zfs_zpool={zfs_zpool}",
            ]
        add_op(
            state,
            server.shell,
            name=f"Configure bastille rc.conf on {host.name}",
            commands=rc_cmds,
            host=host,
        )

        # Install bastille and bootstrap the release
        add_op(
            state,
            server.shell,
            name=f"Install bastille on {host.name}",
            commands=["pkg install -y bastille 2>/dev/null || true"],
            host=host,
        )

        add_op(
            state,
            server.shell,
            name=f"Bootstrap bastille release {release} on {host.name}",
            commands=[
                f"bastille list release 2>/dev/null | grep -q '{release}' "
                f"|| bastille bootstrap {release} update",
            ],
            host=host,
        )

        for jail in jails:
            jail_name = jail["name"]
            jail_release = jail.get("release", release)
            ip = jail.get("ip", "0.0.0.0")
            gateway = jail.get("gateway")
            jail_bridge = jail.get("bridge", bridge)
            thick = jail.get("thick", True)
            static_mac = jail.get("static_mac", True)
            allow_flags = jail.get("allow", {})
            sysvipc = jail.get("sysvipc", False)
            packages = jail.get("packages", [])
            ssh = jail.get("ssh", True)
            authorized_keys_src = jail.get("authorized_keys_src", "/root/.ssh/authorized_keys")
            autostart = jail.get("autostart", True)

            jail_conf = f"/usr/local/bastille/jails/{jail_name}/jail.conf"

            # Build create command
            flags = []
            if thick:
                flags.append("--thick")
            if static_mac:
                flags.append("--bridge --static-mac")
            flags_str = " ".join(flags)

            add_op(
                state,
                server.shell,
                name=f"Create bastille jail {jail_name} on {host.name}",
                commands=[
                    f"test -f {jail_conf} || "
                    f"bastille create {flags_str} {jail_name} {jail_release} {ip} {jail_bridge}",
                ],
                host=host,
            )

            # Jail allow.* config flags
            config_cmds = []
            for flag, value in allow_flags.items():
                config_cmds.append(f"bastille config {jail_name} set allow.{flag} {value}")
            if sysvipc:
                config_cmds += [
                    f"bastille config {jail_name} set sysvmsg new",
                    f"bastille config {jail_name} set sysvsem new",
                    f"bastille config {jail_name} set sysvshm new",
                    f"bastille config {jail_name} set allow.sysvipc 1",
                ]
            if config_cmds:
                add_op(
                    state,
                    server.shell,
                    name=f"Configure jail {jail_name} on {host.name}",
                    commands=config_cmds,
                    host=host,
                )

            # Network configuration
            net_cmds = []
            if ip and ip != "0.0.0.0":
                net_cmds.append(_sysrc(jail_name, "ifconfig_vnet0", f"inet {ip}"))
            if gateway:
                net_cmds.append(_sysrc(jail_name, "defaultrouter", gateway))
            if net_cmds:
                net_cmds.append(
                    f"bastille cmd {jail_name} sh /etc/netstart vnet0 2>/dev/null || true"
                )
                add_op(
                    state,
                    server.shell,
                    name=f"Configure network for jail {jail_name} on {host.name}",
                    commands=net_cmds,
                    host=host,
                )

            # SSH setup
            if ssh:
                add_op(
                    state,
                    server.shell,
                    name=f"Enable sshd in jail {jail_name} on {host.name}",
                    commands=[
                        _sysrc(jail_name, "sshd_enable", "YES"),
                        _sysrc(jail_name, "sshd_flags", "-o PermitRootLogin=yes"),
                        f"bastille service {jail_name} sshd start 2>/dev/null || true",
                    ],
                    host=host,
                )
                add_op(
                    state,
                    server.shell,
                    name=f"Copy authorized_keys into jail {jail_name} on {host.name}",
                    commands=[
                        f"bastille cmd {jail_name} mkdir -p /root/.ssh",
                        f"bastille cp {jail_name} {authorized_keys_src} root/.ssh/authorized_keys",
                        f"bastille cmd {jail_name} chown root:wheel /root/.ssh/authorized_keys",
                    ],
                    host=host,
                )

            # Install packages inside jail
            if packages:
                add_op(
                    state,
                    server.shell,
                    name=f"Install packages in jail {jail_name} on {host.name}",
                    commands=[
                        f"bastille pkg {jail_name} install -y {' '.join(packages)}",
                    ],
                    host=host,
                )

            # Start jail (idempotent)
            add_op(
                state,
                server.shell,
                name=f"Start jail {jail_name} on {host.name}",
                commands=[
                    f"bastille list 2>/dev/null | grep -q ' {jail_name} ' "
                    f"&& bastille restart {jail_name} || bastille start {jail_name}",
                ],
                host=host,
            )

            # Autostart via bastille config boot flag
            if autostart:
                add_op(
                    state,
                    server.shell,
                    name=f"Enable autostart for jail {jail_name} on {host.name}",
                    commands=[
                        f"bastille config {jail_name} set boot on 2>/dev/null || true",
                    ],
                    host=host,
                )
