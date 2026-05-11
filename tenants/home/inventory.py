"""Home infrastructure inventory: 7 hosts (1 OpenBSD, 5 FreeBSD, 1 Debian)."""

from pyinfra.api import Inventory


def build_inventory():
    """Build home infrastructure inventory."""
    all_hosts = [
        ("controller.work", {"_doas": True}),
        ("nas-01.pangea", {"ssh_hostname": "10.50.0.12"}),
        ("virt.home", {"ssh_hostname": "192.168.150.2"}),
        ("virt-01.baar", {"ssh_hostname": "192.168.160.1"}),
        ("virt-02.baar", {"ssh_hostname": "192.168.160.2"}),
        ("virt-03.baar", {"ssh_hostname": "192.168.160.3"}),
        ("docker.home", {}),
    ]

    return Inventory(
        (all_hosts, {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"}),
        # OS groups (privilege escalation config)
        openbsd=(["controller.work"], {"_doas": True}),
        freebsd=(
            ["nas-01.pangea", "virt.home", "virt-01.baar", "virt-02.baar", "virt-03.baar"],
            {"_sudo": True},
        ),
        debian=(["docker.home"], {"_sudo": True, "ssh_user": "debian"}),
        # Location groups (inherit privilege escalation from OS groups)
        work=(["controller.work"], {}),
        pangea=(["nas-01.pangea"], {}),
        home=(["virt.home"], {}),
        baar=(["virt-01.baar", "virt-02.baar", "virt-03.baar"], {}),
        docker=(["docker.home"], {}),
    )
