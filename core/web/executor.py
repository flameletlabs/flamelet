"""Background executor for flamelet deployments."""

import argparse
import sys
import threading
import time
import uuid

from core.cli import build_add_ops_func, load_tenant_inventory, load_tenant_vars_module
from core.runner import run_deployment
from core.web.db import insert_log, insert_run, update_run_status


class LogCapture:
    """Capture stdout/stderr into database in real time."""

    def __init__(self, run_id):
        self.run_id = run_id

    def write(self, line):
        """Write a line to both stdout and database."""
        if line.strip():
            sys.stdout.write(line)
            sys.stdout.flush()
            insert_log(self.run_id, time.time(), line.rstrip())

    def flush(self):
        """Flush stdout."""
        sys.stdout.flush()


def run_deployment_background(run_id, tenant_name, task, target_hosts, dry_run=True):
    """Run a deployment in a background thread."""

    def worker():
        try:
            # Update status to running
            update_run_status(run_id, "running", started_at=time.time())

            # Find tenant path
            from core.paths import get_tenant_path

            tenant_path = get_tenant_path(tenant_name)
            if not tenant_path:
                insert_log(run_id, time.time(), f"ERROR: Tenant '{tenant_name}' not found")
                update_run_status(run_id, "failed", finished_at=time.time())
                return

            # Load inventory and vars
            inventory = load_tenant_inventory(tenant_path)
            tenant_vars = load_tenant_vars_module(tenant_path)

            # Build add_ops function
            add_ops_func = build_add_ops_func(tenant_path, tenant_vars)

            # Redirect stdout to log capture
            old_stdout = sys.stdout
            sys.stdout = LogCapture(run_id)

            try:
                # Build args object for run_deployment
                args = argparse.Namespace(
                    task=task,
                    dry=dry_run,
                    limit=None
                    if target_hosts == ["all"]
                    else target_hosts[0]
                    if target_hosts
                    else None,
                    verbose=True,
                )

                # Run deployment
                exit_code = run_deployment(
                    inventory,
                    add_ops_func,
                    args,
                    verbose=True,
                )

                status = "success" if exit_code == 0 else "failed"
            finally:
                sys.stdout = old_stdout

            update_run_status(run_id, status, finished_at=time.time())

        except Exception as e:
            insert_log(run_id, time.time(), f"ERROR: {e}")
            update_run_status(run_id, "failed", finished_at=time.time())

    # Start background thread
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def queue_run(tenant_name, task, target_hosts=None, dry_run=True):
    """Queue a new run and return the run_id."""
    run_id = str(uuid.uuid4())[:8]
    hosts = target_hosts or ["all"]
    insert_run(run_id, tenant_name, task, hosts, dry_run=dry_run)
    run_deployment_background(run_id, tenant_name, task, hosts, dry_run=dry_run)
    return run_id
