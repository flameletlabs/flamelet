"""Framework CLI entry point: discovers tenant and runs deployment."""

import importlib.util
import sys
from pathlib import Path

from core.paths import find_tenant_path, setup_imports
from core.runner import STANDARD_TASKS, build_parser, run_deployment
from core.tasks import TASK_REGISTRY
from core.tasks.loader import load_packages_config, load_service_config


def load_tenant_inventory(tenant_path: Path):
    """Load inventory.py from tenant.

    Args:
        tenant_path: Path to tenant directory

    Returns:
        pyinfra Inventory object from tenant.build_inventory()
    """
    inventory_file = tenant_path / "inventory.py"
    if not inventory_file.exists():
        raise RuntimeError(f"Tenant inventory.py not found at {inventory_file}")

    spec = importlib.util.spec_from_file_location("inventory", inventory_file)
    inventory_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory_module)

    if not hasattr(inventory_module, "build_inventory"):
        raise RuntimeError("inventory.py must define build_inventory() function")

    return inventory_module.build_inventory()


def load_tenant_vars_module(tenant_path: Path):
    """Load vars/__init__.py from tenant.

    Args:
        tenant_path: Path to tenant directory

    Returns:
        Module object (vars.__init__)
    """
    vars_file = tenant_path / "vars" / "__init__.py"
    if not vars_file.exists():
        raise RuntimeError(f"Tenant vars/__init__.py not found at {vars_file}")

    spec = importlib.util.spec_from_file_location("tenant_vars", vars_file)
    vars_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vars_module)

    return vars_module


def load_tenant_hosts(inventory):
    """Extract host information from inventory.

    Args:
        inventory: pyinfra Inventory object

    Returns:
        List of dicts with {name, os, groups}
    """
    from pyinfra.facts.server import Kernel

    hosts = []
    for host in inventory:
        # Get OS
        try:
            os_key = host.get_fact(Kernel)
        except Exception:
            os_key = "Unknown"

        # Map kernel key to friendly name
        os_name = {
            "Linux": "Linux",
            "FreeBSD": "FreeBSD",
            "OpenBSD": "OpenBSD",
        }.get(os_key, os_key)

        # Get groups
        groups = host.groups if hasattr(host, "groups") else []

        hosts.append({"name": host.name, "os": os_name, "groups": list(groups)})

    return hosts


def build_add_ops_func(tenant_path: Path, tenant_vars, dry: bool = False):
    """Build the add_ops function that dispatches to all operations.

    Args:
        tenant_path: Path to tenant directory
        tenant_vars: Tenant vars module (for USERS, GROUPS, etc.)
        dry: whether dry mode is enabled (threaded to no-config ops like package-update)

    Returns:
        add_ops(state, inventory, target_hosts=None, task="all") function
    """

    def add_ops(state, inventory, target_hosts=None, task="all"):
        """Add operations based on task and TASK_REGISTRY."""
        from pyinfra.facts.server import Kernel

        # Handle special case: task="all" → run all registry tasks
        if task == "all":
            tasks_to_run = list(TASK_REGISTRY.keys())
        else:
            tasks_to_run = [task]

        for task_name in tasks_to_run:
            # Skip hostcheck — it's handled specially in runner.py, not via TASK_REGISTRY
            if task_name == "hostcheck":
                continue

            if task_name not in TASK_REGISTRY:
                print(f"Warning: Unknown task {task_name}, skipping")
                continue

            entries = TASK_REGISTRY[task_name]

            for entry in entries:
                # Pre-filter hosts by OS family if specified
                os_filtered_targets = target_hosts
                if entry.os_families:
                    available_hosts = target_hosts if target_hosts else list(inventory)
                    os_filtered_targets = [
                        h for h in available_hosts if h.get_fact(Kernel) in entry.os_families
                    ]
                    # Skip operation if no hosts match the OS family requirement
                    if not os_filtered_targets:
                        continue

                # Handle users: special case, loads from tenant_vars
                if entry.op_type == "users":
                    entry.op_func(
                        state,
                        inventory,
                        users_config=getattr(tenant_vars, "USERS", {}),
                        group_names=getattr(tenant_vars, "GROUPS", []),
                        target_hosts=os_filtered_targets,
                        task=task_name,
                    )

                # Handle sudo: special case, loads from tenant_vars
                elif entry.op_type == "sudo":
                    entry.op_func(
                        state,
                        inventory,
                        users_config=getattr(tenant_vars, "USERS", {}),
                        target_hosts=os_filtered_targets,
                    )

                # Handle packages: per-host OS detection
                elif entry.op_type == "packages":
                    targets = os_filtered_targets if os_filtered_targets else list(inventory)
                    packages_config = {}
                    for host in targets:
                        os_key = host.get_fact(Kernel)
                        pkg_cfg = load_packages_config(tenant_path, host.name, os_key)
                        if pkg_cfg.get(os_key):
                            packages_config[os_key] = pkg_cfg[os_key]

                    if packages_config:
                        entry.op_func(
                            state, inventory, packages_config, os_filtered_targets, task_name
                        )

                # Handle autossh: dual ops (tunnels + gateway)
                elif entry.op_type == "autossh":
                    config = load_service_config(tenant_path, entry.config_attr)
                    if config:
                        entry.op_func(state, inventory, config, os_filtered_targets, task_name)

                # Handle no-config ops: no tenant vars needed, run directly
                elif entry.op_type == "no-config":
                    entry.op_func(state, inventory, target_hosts=os_filtered_targets, dry=dry)

                # Handle standard service configs
                else:
                    config = load_service_config(tenant_path, entry.config_attr)
                    if config:
                        entry.op_func(state, inventory, config, os_filtered_targets, task_name)

    return add_ops


def main():
    """Main CLI entry point for flamelet."""
    # Setup framework imports
    try:
        setup_imports()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Build parser with all task registry keys
    task_choices = STANDARD_TASKS + list(TASK_REGISTRY.keys())
    parser = build_parser(task_choices=task_choices)
    args = parser.parse_args()

    # Find tenant using --tenant argument (e.g. 'home' -> 'flamelet-home')
    tenant_dir = f"flamelet-{args.tenant}"
    try:
        tenant_path = find_tenant_path(tenant_dir)
    except RuntimeError:
        print(
            f"Error: Tenant '{args.tenant}' not found. Expected: ~/.config/flamelet/tenants/{tenant_dir}/",
            file=sys.stderr,
        )
        return 1

    # Load tenant configuration
    try:
        inventory = load_tenant_inventory(tenant_path)
        tenant_vars = load_tenant_vars_module(tenant_path)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Build the add_ops function
    add_ops = build_add_ops_func(tenant_path, tenant_vars, dry=args.dry)

    # Run deployment
    return run_deployment(inventory, add_ops, args, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
