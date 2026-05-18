"""Deployment orchestration (framework-level)."""

import argparse

from pyinfra.api import Config, State
from pyinfra.api.command import FileUploadCommand, StringCommand
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.operations import run_ops
from pyinfra.api.state import BaseStateCallback
from pyinfra.context import ctx_host, ctx_state

# Framework standard task choices — available on all tenants
STANDARD_TASKS = ["groups", "users", "sudo", "all", "hostcheck"]


class DeploymentCallback(BaseStateCallback):
    """Emits per-operation status lines captured by LogCapture."""

    def __init__(self):
        self._changed = {}  # host.name -> last known success_ops count

    @staticmethod
    def operation_start(state, op_hash):
        names = state.get_op_meta(op_hash).names
        print(f"→ {', '.join(names)}")

    def operation_host_success(self, state, host, op_hash, retry_count=0):
        r = state.results.get(host)
        prev = self._changed.get(host.name, 0)
        curr = r.success_ops if r else 0
        tag = "[CHANGED]" if curr > prev else "[OK]"
        self._changed[host.name] = curr
        print(f"  {tag} {host.name}")

    @staticmethod
    def operation_host_error(state, host, op_hash, *args, **kwargs):
        print(f"  [FAILED] {host.name}")


def _ping_host(hostname, timeout=2):
    """Ping host from control node. Returns (success, latency_ms or None)."""
    import re
    import subprocess

    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), hostname],
            capture_output=True,
            text=True,
            timeout=timeout + 1,
        )
        if result.returncode == 0:
            m = re.search(r"time=(\d+\.?\d*)\s*ms", result.stdout)
            latency = round(float(m.group(1)), 1) if m else None
            return True, latency
        return False, None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, None


def _preview_ops(state, scope):
    """Drain operation generators to show diffs/commands without executing.

    Connects, reads remote facts, and logs diffs (via pyinfra logger) but never
    calls .execute() on any yielded command, so nothing is written to the hosts.
    """
    state.is_executing = True
    try:
        with ctx_state.use(state):
            for op_hash in state.get_op_order():
                names = state.get_op_meta(op_hash).names
                op_label = ", ".join(names)

                for host in scope:
                    if op_hash not in state.ops.get(host, {}):
                        continue

                    op_data = state.get_op_data_for_host(host, op_hash)
                    print(f"→ {op_label}")

                    try:
                        with ctx_host.use(host):
                            yielded = list(op_data.command_generator())

                        if not yielded:
                            print(f"  [OK] {host.name} — no changes")
                        else:
                            print(f"  [CHECK] {host.name} — would apply:")
                            for cmd in yielded:
                                if isinstance(cmd, StringCommand):
                                    print(f"    $ {cmd}")
                                elif isinstance(cmd, FileUploadCommand):
                                    print(f"    upload → {cmd.dest}")
                    except Exception as e:
                        print(f"  [ERROR] {host.name}: {e}")
    finally:
        state.is_executing = False


def build_parser(task_choices=None):
    """Build the CLI argument parser."""
    if task_choices is None:
        task_choices = STANDARD_TASKS

    parser = argparse.ArgumentParser(description="Deploy infrastructure with pyinfra API")
    parser.add_argument("--limit", help="Hostname or group name to deploy to")
    parser.add_argument(
        "--dry", action="store_true", help="Check mode: show what would run without executing"
    )
    parser.add_argument(
        "--diff", action="store_true", help="Show file diffs for operations that write files"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output with debug info"
    )
    parser.add_argument(
        "--task", choices=task_choices, default="all", help="Which task(s) to run (default: all)"
    )
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
    diff = getattr(args, "diff", False)
    config = Config(CONNECT_TIMEOUT=15, DIFF=diff)
    state = State(inventory, config)

    callback = DeploymentCallback()
    state.callback_handlers.append(callback)

    if diff:
        state.print_output = True

    if verbose:
        print(f"[DEBUG] Inventory: {len(list(inventory))} hosts")
        print(f"[DEBUG] Task(s): {args.task}")
        print(f"[DEBUG] Dry-run: {args.dry}")
        if diff:
            print("[DEBUG] Diff: enabled")

    # Apply --limit: filter hosts or group (supports comma-separated hostnames)
    target_hosts = None
    if args.limit:
        names = {n.strip() for n in args.limit.split(",")}
        target_hosts = [h for h in inventory if h.name in names]
        if not target_hosts and len(names) == 1:
            try:
                target_hosts = list(inventory.get_group(args.limit) or [])
            except Exception:
                pass

        if not target_hosts:
            print(f"Error: No hosts matched: {args.limit}")
            return 1

        state.limit_hosts = target_hosts

    # Connect to all active hosts
    print("Connecting to hosts...")
    connect_all(state)
    if verbose:
        print(f"[DEBUG] Connected to {len(list(inventory.get_active_hosts()))} hosts")
        if state.failed_hosts:
            print(f"[DEBUG] Failed hosts: {[h.name for h in state.failed_hosts]}")

    # hostcheck: ping + SSH + uptime/load/kernel, no ops queued
    if args.task == "hostcheck":
        import re

        from pyinfra.facts.server import Kernel

        scope = target_hosts if target_hosts else list(inventory.get_active_hosts())
        any_failed = False

        for host in scope:
            ssh_up = host not in state.failed_hosts

            # Get SSH hostname from host data or use hostname
            ssh_hostname = (host.host_data or {}).get("ssh_hostname", host.name)
            ping_ok, latency_ms = _ping_host(ssh_hostname)

            print(f"\n→ {host.name}")
            ping_str = f"✓ ({latency_ms}ms)" if ping_ok else "✗"
            print(f"  PING:   {ping_str}")
            print(f"  SSH:    {'✓' if ssh_up else '✗'}")

            if not ssh_up:
                any_failed = True
                print("  UPTIME: -   LOAD: -   KERNEL: -   REBOOT: -")
                continue

            # Helper to get shell command output as a single string
            def _shell_out(cmd):
                ok, out = host.run_shell_command(cmd)
                if not ok:
                    return ""
                combined_lines = out.combined_lines if hasattr(out, "combined_lines") else []
                return "\n".join(line_obj.line for line_obj in combined_lines).strip()

            os_key = host.get_fact(Kernel)
            uptime_line = _shell_out("uptime")

            # Parse "up X days, Y hours" from uptime output
            up_m = re.search(r"(up\s+(?:\d+\s+\w+,?\s*)+)", uptime_line)
            uptime_str = up_m.group(1).strip().rstrip(",") if up_m else uptime_line or "-"

            # Load averages (last 3 floats after "load average(s):")
            load_m = re.search(
                r"load\s+averages?:\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)", uptime_line
            )
            load_str = (
                f"{load_m.group(1)} / {load_m.group(2)} / {load_m.group(3)}" if load_m else "-"
            )

            print(f"  UPTIME: {uptime_str}")
            print(f"  LOAD:   {load_str}")
            print(f"  KERNEL: {_shell_out('uname -sr') or '-'}")

            # Reboot required (OS-specific)
            if os_key == "Linux":
                reboot_check = _shell_out("[ -f /run/reboot-required ] && echo yes || echo no")
                reboot_str = "yes" if reboot_check == "yes" else "no"
            elif os_key == "FreeBSD":
                lines = [
                    line
                    for line in _shell_out(
                        "uname -r; freebsd-version -u 2>/dev/null || echo unavailable"
                    ).splitlines()
                    if line
                ]
                if len(lines) >= 2 and lines[0] != lines[1] and lines[1] != "unavailable":
                    reboot_str = f"yes (running {lines[0]}, installed {lines[1]})"
                else:
                    reboot_str = "no"
            else:
                reboot_str = "-"

            print(f"  REBOOT: {reboot_str}")

        disconnect_all(state)
        return 1 if any_failed else 0

    # Exclude hosts that failed to connect so add_ops_func doesn't try
    # fact-reads (change detection) against disconnected hosts.
    if target_hosts:
        target_hosts = [h for h in target_hosts if h not in state.failed_hosts]
        state.limit_hosts = target_hosts if target_hosts else None

    # Queue operations
    print(f"Adding operations (task={args.task})...")
    add_ops_func(state, inventory, target_hosts=target_hosts, task=args.task)
    if verbose:
        print("[DEBUG] Operations queued")

    # package-update in dry mode: execute safe check commands to show available updates
    if args.dry and args.task == "package-update":
        print("Checking available updates...")
        scope = target_hosts if target_hosts else list(inventory.get_active_hosts())

        # Directly run check commands and capture output for display
        from pyinfra.facts.server import Kernel, LinuxDistribution

        for host in scope:
            if host in state.failed_hosts:
                continue

            os_key = host.get_fact(Kernel)

            # Determine check command based on OS
            if os_key == "Linux":
                distro = host.get_fact(LinuxDistribution) or {}
                distro_id = distro.get("id", "").lower()
                if distro_id == "alpine":
                    check_cmd = "sudo apk update -q && sudo apk upgrade -s"
                else:
                    check_cmd = "sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq && sudo apt-get upgrade --dry-run"
            elif os_key == "FreeBSD":
                check_cmd = "sudo pkg update -q && sudo pkg upgrade -n"
            elif os_key == "OpenBSD":
                check_cmd = "sudo pkg_add -u -n"
            else:
                continue

            # Run check command on host and display output
            print(f"\n→ {host.name}:")
            try:
                success, output = host.run_shell_command(check_cmd)
                if output and hasattr(output, "combined_lines"):
                    for output_line in output.combined_lines:
                        if output_line.line.strip():
                            print(f"  {output_line.line}")
                elif not success:
                    print("  [ERROR] Command failed")
            except Exception as e:
                print(f"  [ERROR] {e}")

        disconnect_all(state)
        return 0

    # Check mode: show what would run without executing
    if args.dry:
        active = list(inventory.get_active_hosts())
        scope = target_hosts if target_hosts else active

        if diff:
            # Deep check: drain generators to read remote state and show diffs
            print("Checking remote state (diff mode)...")
            _preview_ops(state, scope)
        else:
            # Shallow check: list operation names only
            total = 0
            for host in scope:
                host_ops = state.ops.get(host, {})
                count = len(host_ops)
                total += count
                if count == 0:
                    print(f"[CHECK] {host.name} — no operations queued")
                else:
                    noun = "operation" if count == 1 else "operations"
                    print(f"[CHECK] {host.name} — {count} {noun}:")
                    seen = set()
                    for op_hash in state.get_op_order():
                        if op_hash in host_ops and op_hash not in seen:
                            seen.add(op_hash)
                            names = state.get_op_meta(op_hash).names
                            print(f"  • {', '.join(names)}")
            print(f"\n[CHECK] Total: {total} operation(s) across {len(scope)} host(s)")

        disconnect_all(state)
        return 0

    # Execute
    print("Running operations...")
    aborted = False
    try:
        run_ops(state)
    except PyinfraError as e:
        print(f"[FAILED] {e}")
        aborted = True
    finally:
        disconnect_all(state)

    # Summary — always shown, even after a partial abort
    print("\n=== Summary ===")
    exit_code = 1 if aborted else 0

    all_hosts = set(inventory.get_active_hosts()) | state.failed_hosts
    for host in all_hosts:
        r = state.results.get(host)
        if host in state.failed_hosts and not r:
            print(f"✗ {host.name:<30} connection failed")
            continue
        if r:
            changed = callback._changed.get(host.name, 0)
            ok = r.success_ops - changed
            failed = r.error_ops
            status = "✓" if failed == 0 else "✗"
            print(f"{status} {host.name:<30} {changed} changed   {ok} ok   {failed} failed")
            if failed > 0:
                exit_code = 1
        else:
            print(f"? {host.name:<30} no operations run")

    return exit_code
