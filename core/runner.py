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
        # host.name -> number of operations that ACTUALLY CHANGED something.
        #
        # This used to hold the last known success_ops count, which made every
        # line read [CHANGED] and every summary read "N changed 0 ok". success_ops
        # counts operations that RAN, not operations that changed anything, so it
        # increments for a no-op too -- and `ok = success_ops - changed` then
        # always lands on zero. A converged host cannot have zero satisfied
        # operations, so "0 ok" was the tell.
        #
        # Why it mattered beyond cosmetics: the whole point of a converging
        # deployer is that its output tells you what it did. Reporting 28 changes
        # where 3 files were written means a deploy that quietly rewrote something
        # is indistinguishable from one that did not, and answering "what changed?"
        # needs a SECOND --dry --diff run. It also actively misleads: a spurious
        # "changed" next to a service restart reads as a config change that never
        # happened.
        self._changed = {}
        # op_hash -> [hosts that succeeded], awaiting operation_end so
        # did_change() can be read. See operation_host_success.
        self._pending = {}
        # host.name -> [operation names that failed]. pyinfra's per-host
        # result.error_ops does NOT count every failure -- a connector-level
        # error (e.g. SFTP unavailable) raises out of the greenlet without
        # incrementing it -- so the summary cannot rely on that alone.
        self._errors = {}

    @staticmethod
    def operation_start(state, op_hash):
        names = state.get_op_meta(op_hash).names
        print(f"→ {', '.join(names)}")

    def operation_host_success(self, state, host, op_hash, retry_count=0):
        # DEFERRED ON PURPOSE -- do not print here.
        #
        # The honest answer to "did this change anything" is
        # op_data.operation_meta.did_change(), which is
        # `success and len(commands) > 0`: an operation that generated no
        # commands changed nothing. That is the same signal the --diff path
        # already uses (a command_generator yielding nothing prints "no
        # changes"), which is why apply and --dry --diff used to disagree.
        #
        # But it CANNOT be read here. pyinfra triggers this callback at
        # operations.py:211 and only calls op_data.operation_meta.set_complete()
        # at :237 -- afterwards -- so did_change() raises "Cannot evaluate
        # operation result before execution" at this point. Reading it here was
        # my first attempt and it silently fell through to the old heuristic,
        # which is exactly the bug. operation_end (:378) fires after every host's
        # set_complete, so the tag is emitted there instead.
        #
        # pyinfra 3.8 has no changed_ops counter to read instead -- the results
        # object exposes only error_ops / ignored_error_ops / ops / partial_ops /
        # success_ops.
        self._pending.setdefault(op_hash, []).append(host)

    def operation_end(self, state, op_hash):
        """Emit one status line per host, now that did_change() is answerable."""
        for host in self._pending.pop(op_hash, []):
            changed = True  # fall back to the old, over-reporting behaviour
            try:
                op_data = state.get_op_data_for_host(host, op_hash)
                changed = op_data.operation_meta.did_change()
            except Exception:
                # These internals are not a public contract. Degrade loudly in
                # the direction of over-reporting rather than under-reporting: a
                # missed change reads as "nothing happened", which is worse than
                # a spurious one.
                pass

            if changed:
                self._changed[host.name] = self._changed.get(host.name, 0) + 1
            print(f"  {'[CHANGED]' if changed else '[OK]'} {host.name}")

    def operation_host_error(self, state, host, op_hash, *args, **kwargs):
        # RECORD, do not merely print. This used to be a staticmethod that only
        # printed, so nothing downstream knew a host had failed and the summary
        # happily reported it green.
        try:
            names = ", ".join(state.get_op_meta(op_hash).names)
        except Exception:
            names = "unknown operation"
        self._errors.setdefault(host.name, []).append(names)
        print(f"  [FAILED] {host.name}: {names}")


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

    Returns {host name: {"would_apply": int, "unchanged": int, "errors": int}} so
    the caller can print a per-host tally. Callers used to reconstruct that by
    grepping this function's output for "would apply", which silently reports
    zero for any host that never got far enough to print the string at all.
    """
    stats = {host.name: {"would_apply": 0, "unchanged": 0, "errors": 0} for host in scope}
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
                            stats[host.name]["unchanged"] += 1
                        else:
                            print(f"  [CHECK] {host.name} — would apply:")
                            stats[host.name]["would_apply"] += 1
                            for cmd in yielded:
                                if isinstance(cmd, StringCommand):
                                    print(f"    $ {cmd}")
                                elif isinstance(cmd, FileUploadCommand):
                                    print(f"    upload → {cmd.dest}")
                    except Exception as e:
                        print(f"  [ERROR] {host.name}: {e}")
                        stats[host.name]["errors"] += 1
    finally:
        state.is_executing = False
    return stats


def _print_dry_summary(targeted, failed_hosts, stats, evaluated_drift, header="Dry-run summary"):
    """Print one line per TARGETED host and return the process exit code.

    A dry run had no way to say "I did not measure this host". Every outcome
    below printed either nothing or something a reader takes for good news:

      host was never reached      omitted from the active-host list entirely, so
                                  it produced no output at all
      host failed mid-run         a traceback above, then no per-host line
      no --diff                   operation names with no status, and grepping
                                  for "would apply" returns 0, which reads CLEAN
      genuinely nothing to do     "no operations queued"

    Only the last is good news, and all four looked alike in a bulk sweep. So
    every targeted host now gets a line whether or not it was measured, hosts
    that were not measured say so in those words, and an unreachable host makes
    the command exit non-zero instead of 0. Callers can then trust the exit code
    and stop reconstructing a verdict by grepping.
    """
    failed_names = {host.name for host in failed_hosts}

    print(f"\n=== {header} ===")
    unreachable = 0
    for host in targeted:
        if host.name in failed_names:
            unreachable += 1
            print(f"  {host.name}: FAILED — could not connect, NOT evaluated")
        elif not evaluated_drift:
            print(f"  {host.name}: not evaluated for drift (no --diff)")
        else:
            counts = stats.get(host.name) or {"would_apply": 0, "unchanged": 0, "errors": 0}
            line = (
                f"  {host.name}: {counts['would_apply']} would apply, "
                f"{counts['unchanged']} unchanged"
            )
            if counts["errors"]:
                line += f", {counts['errors']} ERRORED"
            print(line)

    if unreachable:
        print(
            f"\n[CHECK] {len(targeted) - unreachable} of {len(targeted)} host(s) evaluated; "
            f"{unreachable} could NOT be reached — this run does not tell you "
            f"whether they have drifted."
        )
        return 1

    if not evaluated_drift:
        print(
            "\n[CHECK] This was a PLAN LISTING, not a drift report. It names the "
            "operations that would be considered; it does NOT check whether each "
            "one is already satisfied. Re-run with --diff to evaluate drift."
        )
    return 0


def build_parser(task_choices=None):
    """Build the CLI argument parser."""
    if task_choices is None:
        task_choices = STANDARD_TASKS

    parser = argparse.ArgumentParser(description="Deploy infrastructure with pyinfra API")
    parser.add_argument(
        "--tenant",
        required=True,
        help="Tenant name (e.g. 'home' maps to ~/.config/flamelet/tenants/flamelet-example/)",
    )
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

    # Connect to all active hosts.
    #
    # When EVERY targeted host fails, pyinfra raises "No hosts remaining!" from
    # inside connect_all. Uncaught, that surfaced as a bare traceback -- so the
    # single most common way to target a set of unreachable hosts produced a
    # crash, not a report, and a bulk sweep could not tell it apart from a host
    # with nothing to do. The hosts are already recorded in state.failed_hosts by
    # the time it raises, so there is nothing to recover: carry on and let the
    # per-host summary below say plainly which hosts were never reached.
    print("Connecting to hosts...")
    try:
        connect_all(state)
    except PyinfraError as e:
        print(f"[FAILED] {e}")

    # With nothing connected there is no state to read, and queueing operations
    # would fault gathering facts from hosts that are not there. hostcheck is the
    # exception: reporting that a host is down is precisely its job.
    if args.task != "hostcheck" and not list(inventory.get_active_hosts()):
        _print_dry_summary(
            target_hosts if target_hosts else list(state.failed_hosts),
            state.failed_hosts,
            None,
            False,
            header="Summary — no host could be reached",
        )
        disconnect_all(state)
        return 1

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
    #
    # THIS MUST NOT BE CONDITIONAL ON target_hosts. It used to read
    # `if target_hosts:`, which meant the filter ran only when --limit was
    # given. Without --limit, target_hosts is empty, the filter was skipped
    # entirely, and add_ops fell back to `list(inventory)` -- every host,
    # including the ones that had just failed to connect. Building operations
    # then calls host.get_fact(Kernel), which re-dials with
    # raise_exceptions=True, and the run died on an unhandled ConnectError.
    #
    # So the single most common invocation -- a full-inventory sweep with no
    # --limit -- crashed whenever ANY host was unreachable, which is the normal
    # state of a fleet spanning several sites. Worse, it crashed in exactly the
    # case this dry-run reporting exists to describe: it could not tell you a
    # host was unreachable, because being unable to reach it killed the run.
    scope = target_hosts if target_hosts else list(inventory.get_active_hosts())
    target_hosts = [h for h in scope if h not in state.failed_hosts]
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

        # A host that failed to connect is no longer "active", so a scope built
        # from active hosts alone quietly loses it -- and losing a host is
        # exactly the outcome that must not pass unremarked. Report on what was
        # TARGETED, then measure only the subset that is actually reachable.
        targeted = target_hosts if target_hosts else (active + list(state.failed_hosts))
        scope = [host for host in targeted if host not in state.failed_hosts]

        if diff:
            # Deep check: drain generators to read remote state and show diffs
            print("Checking remote state (diff mode)...")
            stats = _preview_ops(state, scope)
        else:
            stats = None
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

        exit_code = _print_dry_summary(targeted, state.failed_hosts, stats, diff)
        disconnect_all(state)
        return exit_code

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
            # r.error_ops ALONE IS NOT ENOUGH. A connector-level failure -- the
            # real case that motivated this: sftp disabled on the host -- raises
            # out of the greenlet without ever incrementing error_ops, so a run
            # that failed to upload a single file reported
            #   ✓ core.london   1 changed   0 ok   0 failed
            # while /etc/monitrc kept the previous day's contents. Take the
            # worst of every signal available, and treat an aborted run as a
            # failure for every host rather than trusting a per-host counter
            # that demonstrably undercounts.
            errs = callback._errors.get(host.name, [])
            failed = max(r.error_ops, len(errs))
            status = "✓" if (failed == 0 and not aborted) else "✗"
            suffix = "" if failed or not aborted else "   (run aborted)"
            print(f"{status} {host.name:<30} {changed} changed   {ok} ok   {failed} failed{suffix}")
            for name in errs:
                print(f"    ↳ failed: {name}")
            if failed > 0:
                exit_code = 1
        else:
            print(f"? {host.name:<30} no operations run")

    if aborted:
        # Say it in words as well as in the tick. A summary is the thing people
        # read INSTEAD of the scrollback; if it is green they will not scroll.
        print(
            "\n[ABORTED] The run did not complete. Do NOT treat the above as "
            "deployed — re-run and confirm before relying on it."
        )

    return exit_code
