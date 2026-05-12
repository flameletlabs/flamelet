#!/usr/bin/env python3
"""Home tenant deployment orchestration with full service operations support."""

import sys
from pathlib import Path

# Import setup_imports before framework modules
# This works even if core/ is not in sys.path yet
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.paths import setup_imports  # noqa: E402

setup_imports()

from core.operations.sudo import add_sudoers_ops  # noqa: E402
from core.operations.users import add_user_ops  # noqa: E402
from core.operations.wireguard import add_wireguard_ops  # noqa: E402
from core.operations.unbound import add_unbound_ops  # noqa: E402
from core.operations.monit import add_monit_ops  # noqa: E402
from core.operations.pf import add_pf_ops  # noqa: E402
from core.operations.docker import add_docker_ops  # noqa: E402
from core.operations.node_exporter import add_node_exporter_ops  # noqa: E402
from core.operations.opensmtpd import add_opensmtpd_ops  # noqa: E402
from core.operations.services import add_service_ops  # noqa: E402
from core.runner import STANDARD_TASKS, build_parser, run_deployment  # noqa: E402
from tenants.home import vars as tenant_vars  # noqa: E402
from tenants.home.inventory import build_inventory  # noqa: E402

# Service operations available on top of standard tasks
SERVICE_TASKS = [
    "wireguard",
    "unbound",
    "monit",
    "pf",
    "docker",
    "node_exporter",
    "opensmtpd",
]

# All available task choices for this tenant
TENANT_TASKS = STANDARD_TASKS + SERVICE_TASKS


def add_ops(state, inventory, target_hosts=None, task="all"):
    """Add all operations for home tenant."""
    # Phase 1: Foundation
    add_user_ops(
        state,
        inventory,
        users_config=tenant_vars.USERS,
        group_names=tenant_vars.GROUPS,
        target_hosts=target_hosts,
        task=task,
    )
    if task in ("sudo", "all"):
        add_sudoers_ops(
            state,
            inventory,
            users_config=tenant_vars.USERS,
            target_hosts=target_hosts,
        )

    # Phase 3: Network & Security
    if task in ("wireguard", "all"):
        add_wireguard_ops(
            state,
            inventory,
            config=tenant_vars.get_wireguard_config(),
            target_hosts=target_hosts,
            task=task,
        )

    if task in ("unbound", "all"):
        add_unbound_ops(
            state,
            inventory,
            config=tenant_vars.get_unbound_config(),
            target_hosts=target_hosts,
            task=task,
        )

    if task in ("pf", "all"):
        add_pf_ops(
            state,
            inventory,
            config=tenant_vars.get_pf_config(),
            target_hosts=target_hosts,
            task=task,
        )

    # Phase 4: Monitoring & Observability
    if task in ("monit", "all"):
        add_monit_ops(
            state,
            inventory,
            config=tenant_vars.get_monit_config(),
            target_hosts=target_hosts,
            task=task,
        )

    if task in ("node_exporter", "all"):
        add_node_exporter_ops(
            state,
            inventory,
            config=tenant_vars.get_node_exporter_config(),
            target_hosts=target_hosts,
            task=task,
        )

    # Phase 5: Mail & Communication
    if task in ("opensmtpd", "all"):
        add_opensmtpd_ops(
            state,
            inventory,
            config=tenant_vars.get_opensmtpd_config(),
            target_hosts=target_hosts,
            task=task,
        )

    # Phase 6: Containers (Docker)
    if task in ("docker", "all"):
        add_docker_ops(
            state,
            inventory,
            config=tenant_vars.get_docker_config(),
            target_hosts=target_hosts,
            task=task,
        )


def main():
    parser = build_parser(task_choices=TENANT_TASKS)
    args = parser.parse_args()

    inventory = build_inventory()
    return run_deployment(inventory, add_ops, args, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
