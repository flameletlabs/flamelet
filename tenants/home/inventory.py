"""Example home infrastructure inventory: 7 hosts (1 OpenBSD, 5 FreeBSD, 1 Debian)."""

from pyinfra.api import Inventory


def build_inventory():
    """Build example home infrastructure inventory."""
    all_hosts = [
        ("gw.example.com", {"_doas": True}),  # OpenBSD gateway (example)
        ("nas.example.com", {"ssh_hostname": "10.0.0.10"}),  # FreeBSD NAS (example)
        ("hypervisor.example.com", {"ssh_hostname": "10.0.0.50"}),  # FreeBSD hypervisor (example)
        ("worker-1.example.com", {"ssh_hostname": "10.0.0.51"}),  # FreeBSD worker (example)
        ("worker-2.example.com", {"ssh_hostname": "10.0.0.52"}),  # FreeBSD worker (example)
        ("worker-3.example.com", {"ssh_hostname": "10.0.0.53"}),  # FreeBSD worker (example)
        ("docker.example.com", {}),  # Debian build host (example)
    ]

    return Inventory(
        (all_hosts, {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"}),
        # OS groups (privilege escalation config)
        openbsd=(["gw.example.com"], {"_doas": True}),
        freebsd=(
            ["nas.example.com", "hypervisor.example.com", "worker-1.example.com", "worker-2.example.com", "worker-3.example.com"],
            {"_sudo": True},
        ),
        debian=(["docker.example.com"], {"_sudo": True, "ssh_user": "debian"}),
        # Location/functional groups
        gateway=(["gw.example.com"], {}),
        storage=(["nas.example.com"], {}),
        hypervisors=(["hypervisor.example.com"], {}),
        workers=(["worker-1.example.com", "worker-2.example.com", "worker-3.example.com"], {}),
        docker=(["docker.example.com"], {}),
    )
