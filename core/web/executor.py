"""Background executor for flamelet deployments."""

import argparse
import logging
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
        self._real_stdout = sys.stdout  # snapshot before replacement to avoid recursion

    def write(self, line):
        if line.strip():
            self._real_stdout.write(line)
            self._real_stdout.flush()
            insert_log(self.run_id, time.time(), line.rstrip())

    def flush(self):
        self._real_stdout.flush()


def run_deployment_background(run_id, tenant_name, task, target_hosts, dry_run=True, diff=False):
    """Run a deployment in a background thread."""

    def worker():
        try:
            update_run_status(run_id, "running", started_at=time.time())

            from core.paths import get_tenant_path

            tenant_path = get_tenant_path(tenant_name)
            if not tenant_path:
                insert_log(run_id, time.time(), f"ERROR: Tenant '{tenant_name}' not found")
                update_run_status(run_id, "failed", finished_at=time.time())
                return

            inventory = load_tenant_inventory(tenant_path)
            tenant_vars = load_tenant_vars_module(tenant_path)
            add_ops_func = build_add_ops_func(tenant_path, tenant_vars, dry=dry_run)

            old_stdout = sys.stdout
            sys.stdout = LogCapture(run_id)

            # Forward pyinfra's own logger (diffs, status lines) into the log stream
            pyinfra_logger = logging.getLogger("pyinfra")
            log_handler = logging.StreamHandler(sys.stdout)
            log_handler.setLevel(logging.INFO)
            log_handler.setFormatter(logging.Formatter("%(message)s"))
            pyinfra_logger.addHandler(log_handler)

            try:
                limit = None
                if target_hosts and target_hosts != ["all"]:
                    limit = ",".join(target_hosts)

                args = argparse.Namespace(
                    task=task,
                    dry=dry_run,
                    diff=diff,
                    limit=limit,
                    verbose=True,
                )

                exit_code = run_deployment(
                    inventory,
                    add_ops_func,
                    args,
                    verbose=True,
                )

                status = "success" if exit_code == 0 else "failed"
            finally:
                pyinfra_logger.removeHandler(log_handler)
                sys.stdout = old_stdout

            update_run_status(run_id, status, finished_at=time.time())

        except Exception as e:
            insert_log(run_id, time.time(), f"ERROR: {e}")
            update_run_status(run_id, "failed", finished_at=time.time())

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def queue_run(tenant_name, task, target_hosts=None, dry_run=True, diff=False):
    """Queue a new run and return the run_id."""
    run_id = str(uuid.uuid4())[:8]
    hosts = target_hosts or ["all"]
    insert_run(run_id, tenant_name, task, hosts, dry_run=dry_run)
    run_deployment_background(run_id, tenant_name, task, hosts, dry_run=dry_run, diff=diff)
    return run_id
