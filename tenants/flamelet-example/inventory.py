"""Example infrastructure inventory: 8 hosts across London and New York."""

import os

from pyinfra.api import Inventory


def build_inventory(local=False):
    """Build example infrastructure inventory across two global locations.

    Args:
        local: If True, use @local connector (for CI/testing without SSH).
               This runs operations on the local machine instead of via SSH.
               Can also be triggered by FLAMELET_LOCAL environment variable.
    """
    # Check environment variable for CI environments that can't pass parameters
    if not local and os.environ.get("FLAMELET_LOCAL", "").lower() in ("1", "true", "yes"):
        local = True

    if local:
        # CI/testing mode: use @local connector (no SSH needed)
        return Inventory(
            (
                [("@local", {"_sudo": True})],
                {},
            ),
        )
    all_hosts = [
        # London (4 hosts)
        ("gw.london", {"ssh_hostname": "10.10.0.1"}),  # OpenBSD gateway
        ("web-01.london", {"ssh_hostname": "10.10.0.11"}),  # FreeBSD web server
        ("web-02.london", {"ssh_hostname": "10.10.0.12"}),  # FreeBSD web server
        ("db.london", {"ssh_hostname": "10.10.0.20"}),  # Debian database
        # New York (4 hosts)
        ("gw.newyork", {"ssh_hostname": "10.20.0.1"}),  # OpenBSD gateway
        ("worker-01.newyork", {"ssh_hostname": "10.20.0.11"}),  # FreeBSD compute worker
        ("worker-02.newyork", {"ssh_hostname": "10.20.0.12"}),  # FreeBSD compute worker
        ("docker.newyork", {"ssh_hostname": "10.20.0.30"}),  # Debian container host
    ]

    return Inventory(
        (all_hosts, {"ssh_user": "syseng", "ssh_key": "~/.ssh/id_rsa"}),
        # OS groups (privilege escalation config)
        openbsd=(["gw.london", "gw.newyork"], {"_doas": True}),
        freebsd=(
            [
                "web-01.london",
                "web-02.london",
                "worker-01.newyork",
                "worker-02.newyork",
            ],
            {"_sudo": True},
        ),
        debian=(["db.london", "docker.newyork"], {"_sudo": True, "ssh_user": "debian"}),
        # Location groups (for --limit targeting)
        london=(["gw.london", "web-01.london", "web-02.london", "db.london"], {}),
        newyork=(["gw.newyork", "worker-01.newyork", "worker-02.newyork", "docker.newyork"], {}),
        # Functional groups
        gateway=(["gw.london", "gw.newyork"], {}),
        web=(["web-01.london", "web-02.london"], {}),
        workers=(["worker-01.newyork", "worker-02.newyork"], {}),
        docker=(["docker.newyork"], {}),
    )
