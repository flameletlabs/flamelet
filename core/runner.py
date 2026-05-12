"""Deployment orchestration (framework-level)."""

import argparse
import sys

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.operations import run_ops

# Framework standard task choices — available on all tenants
STANDARD_TASKS = ["groups", "users", "sudo", "all"]


def build_parser(task_choices=None):
    """Build the CLI argument parser.

    Args:
        task_choices: List of available tasks. If None, uses STANDARD_TASKS.
                      To extend with custom tasks, pass STANDARD_TASKS + ["custom_task"]
    """
    if task_choices is None:
        task_choices = STANDARD_TASKS

    parser = argparse.ArgumentParser(description="Deploy infrastructure with pyinfra API")
    parser.add_argument("--limit", help="Hostname or group name to deploy to")
    parser.add_argument("--dry", action="store_true", help="Validate without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output with debug info")
    parser.add_argument("--task", choices=task_choices, default="all",
                        help="Which task(s) to run (default: all)")
    return parser


def run_deployment(inventory, add_ops_func, args, verbose=False):
    """Execute deployment with given inventory and operations function.

    Args:
        inventory: pyinfra Inventory object
        add_ops_func: callable(state, inventory, target_hosts, task) that queues operations
        args: parsed arguments from argparse
        verbose: whether to print debug info

    Returns:
        exit code (0 for success, 1 for failure)
    """
    config = Config(CONNECT_TIMEOUT=15, DRY=args.dry)
    state = State(inventory, config)

    if verbose:
        print(f"[DEBUG] Inventory: {len(list(inventory))} hosts")
        print(f"[DEBUG] Task(s): {args.task}")
        print(f"[DEBUG] Dry-run: {args.dry}")

    # Apply --limit: filter hosts or group
    target_hosts = None
    if args.limit:
        target_hosts = [h for h in inventory if h.name == args.limit]
        if not target_hosts:
            try:
                target_hosts = list(inventory.get_group(args.limit) or [])
            except Exception:
                pass

        if not target_hosts:
            print(f"Error: No hosts matched: {args.limit}")
            return 1

        # Limit to specific hosts
        state.limit_hosts = target_hosts

    # Connect to all active hosts
    print("Connecting to hosts...")
    connect_all(state)
    if verbose:
        print(f"[DEBUG] Connected to {len(list(inventory.get_active_hosts()))} hosts")
        if state.failed_hosts:
            print(f"[DEBUG] Failed hosts: {[h.name for h in state.failed_hosts]}")

    # Add operations
    print(f"Adding operations (task={args.task})...")
    add_ops_func(state, inventory, target_hosts=target_hosts, task=args.task)
    if verbose:
        print("[DEBUG] Operations queued")

    # Execute
    print("Running operations...")
    try:
        run_ops(state)
    except PyinfraError as e:
        print(f"Error during deployment: {e}", file=sys.stderr)
        return 1
    finally:
        disconnect_all(state)

    # Print results
    print("\n=== Deployment Results ===")
    exit_code = 0
    for host in inventory.get_active_hosts():
        r = state.results.get(host)
        if r:
            status = "✓" if r.error_ops == 0 else "✗"
            print(f"{status} {host.name}: {r.success_ops}/{r.ops} ops ok, {r.error_ops} errors")
            if r.error_ops > 0:
                exit_code = 1
        else:
            print(f"? {host.name}: no operations run")

    return exit_code if not state.failed_hosts else 1
