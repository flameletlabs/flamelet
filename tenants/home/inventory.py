"""Example home infrastructure inventory: 7 hosts (1 OpenBSD, 5 FreeBSD, 1 Debian)."""

from pyinfra.api import Inventory


def build_inventory():
    """Build example home infrastructure inventory."""
    all_hosts = [
        ("gw.example.com", {"_doas": True}),  # OpenBSD gateway (example)
        ("nas.example.com", {"ssh_hostname": "10.0.2.10"}),  # FreeBSD NAS (example)
        ("hypervisor.local", {"ssh_hostname": "192.168.1.50"}),  # FreeBSD hypervisor (example)
        ("worker-1.local", {"ssh_hostname": "192.168.1.51"}),  # FreeBSD worker (example)
        ("worker-2.local", {"ssh_hostname": "192.168.1.52"}),  # FreeBSD worker (example)
        ("worker-3.local", {"ssh_hostname": "192.168.1.53"}),  # FreeBSD worker (example)
        ("docker-build.local", {}),  # Debian build host (example)
    ]

    return Inventory(
        (all_hosts, {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"}),
        # OS groups (privilege escalation config)
        openbsd=(["gw.example.com"], {"_doas": True}),
        freebsd=(
            ["nas.example.com", "hypervisor.local", "worker-1.local", "worker-2.local", "worker-3.local"],
            {"_sudo": True},
        ),
        debian=(["docker-build.local"], {"_sudo": True, "ssh_user": "debian"}),
        # Location/functional groups
        gateway=(["gw.example.com"], {}),
        storage=(["nas.example.com"], {}),
        hypervisors=(["hypervisor.local"], {}),
        workers=(["worker-1.local", "worker-2.local", "worker-3.local"], {}),
        docker=(["docker-build.local"], {}),
    )
