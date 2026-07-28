"""Watchcat (OpenWrt/GL.iNet connectivity watchdog) configuration via UCI."""

from pyinfra.api.operation import add_op
from pyinfra.operations import server


def add_watchcat_ops(state, hosts, config, target_hosts=None, task="all"):
    """Configure watchcat connectivity watchdog settings on OpenWrt devices.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname -> watchcat config
            {
                "uplink-2.madrid": {
                    "section": "watchcat.@watchcat[0]",   # UCI section reference (default: "watchcat.@watchcat[0]")
                    "mode": "restart_iface",       # periodic_reboot | ping_reboot | restart_iface | run_script
                    "period": "10m",
                    "pinghosts": ["1.1.1.1", "8.8.8.8"],
                    "pingperiod": 60,
                    "pingsize": "standard",
                    "addressfamily": "any",
                    "interface": None,             # optional: restart_iface/run_script target device.
                                                    # Left unset, restart_iface falls back to a full
                                                    # `/etc/init.d/network restart` instead of a single
                                                    # interface bounce.
                }
            }
        target_hosts: list of Host objects (default: all)
        task: "watchcat" or "all"
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        wc_config = config[host.name]
        section = wc_config.get("section", "watchcat.@watchcat[0]")

        uci_sets = [f"uci set {section}.mode='{wc_config['mode']}'"]

        if "period" in wc_config:
            uci_sets.append(f"uci set {section}.period='{wc_config['period']}'")
        if "pinghosts" in wc_config:
            pinghosts_str = " ".join(wc_config["pinghosts"])
            uci_sets.append(f"uci set {section}.pinghosts='{pinghosts_str}'")
        if "pingperiod" in wc_config:
            uci_sets.append(f"uci set {section}.pingperiod='{wc_config['pingperiod']}'")
        if "pingsize" in wc_config:
            uci_sets.append(f"uci set {section}.pingsize='{wc_config['pingsize']}'")
        if "addressfamily" in wc_config:
            uci_sets.append(f"uci set {section}.addressfamily='{wc_config['addressfamily']}'")
        if wc_config.get("interface"):
            uci_sets.append(f"uci set {section}.interface='{wc_config['interface']}'")
        if wc_config.get("script"):
            uci_sets.append(f"uci set {section}.script='{wc_config['script']}'")

        uci_sets.append("uci commit watchcat")

        add_op(
            state,
            server.shell,
            name=f"Configure watchcat on {host.name}",
            commands=[" && ".join(uci_sets)],
            host=host,
        )

        # procd instance needs a clean stop/start to pick up a mode change -
        # a reload trigger alone won't re-exec watchcat.sh with new args.
        add_op(
            state,
            server.shell,
            name=f"Restart watchcat service on {host.name}",
            commands=["/etc/init.d/watchcat restart"],
            host=host,
        )
