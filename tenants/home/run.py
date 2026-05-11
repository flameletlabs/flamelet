#!/usr/bin/env python3
"""Home tenant deployment orchestration (example tenant entry point)."""

import sys
from pathlib import Path

# Import setup_imports before framework modules
# This works even if core/ is not in sys.path yet
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.paths import setup_imports  # noqa: E402

setup_imports()

from core.operations.sudo import add_sudoers_ops  # noqa: E402
from core.operations.users import add_user_ops  # noqa: E402
from core.runner import STANDARD_TASKS, build_parser, run_deployment  # noqa: E402
from tenants.home import vars as tenant_vars  # noqa: E402
from tenants.home.inventory import build_inventory  # noqa: E402


def add_ops(state, inventory, target_hosts=None, task="all"):
    """Add all operations for home tenant (example)."""
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


def main():
    parser = build_parser()  # Uses STANDARD_TASKS from framework
    args = parser.parse_args()

    inventory = build_inventory()
    return run_deployment(inventory, add_ops, args, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
