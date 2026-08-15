"""VyOS appliance configuration, applied through its own CLI.

VyOS is IMAGE-MANAGED. Its filesystem is not the source of truth and reaching
under it with apt or by editing files is unsupported and can break an image
upgrade -- so this operation drives `set`/`delete` through the config CLI, which
is the only interface the vendor supports.

Config attribute: VYOS (hostname-keyed)

    VYOS = {
        "gateway.example.com": {
            "set": [
                # everything AFTER the word `set`
                "service monitoring prometheus node-exporter listen-address 10.0.0.1",
                "service monitoring prometheus node-exporter port 9100",
            ],
            "delete": [
                "service telnet",
            ],
        }
    }

THREE SAFETY PROPERTIES, each of which exists because of a specific way this
goes wrong on a live router.

1. IT REFUSES TO RUN ON A DIRTY CANDIDATE. `commit` applies the ENTIRE candidate
   configuration, not just the lines this operation set. If a human left changes
   uncommitted in another session, a deploy would silently ship them -- on the
   box that routes a whole site. So the script compares first and aborts with a
   non-zero exit if anything is already pending, rather than "helpfully"
   committing someone else's half-finished work.

2. IT ALWAYS `save`s AFTER `commit`. A commit without a save is lost on the next
   reboot, and the failure is invisible until then: the config is live, the
   service answers, everything looks correct, and it evaporates.

3. IT DISCARDS INSTEAD OF COMMITTING WHEN NOTHING CHANGED. `set` on an existing
   value is a no-op, so a second run produces an empty diff; committing an empty
   diff would still bump the config revision and make every run look like a
   change. Comparing after the sets is what makes this operation honestly
   idempotent.

⚠️ NEVER ADD `set -e` TO THE GENERATED SCRIPT. Inside VyOS's script-template
`set` is redefined as the configuration command, so `set -e` is parsed as a
CONFIG statement -- it does not enable errexit, it tries to configure a node
called "-e". The same applies to any other shell builtin the template shadows.
"""

from io import StringIO

from pyinfra.api.operation import add_op
from pyinfra.operations import files, server

# Where the generated script lands on the appliance. Written, run, removed --
# nothing is left behind for a later run to inherit.
SCRIPT = "/tmp/.flamelet-vyos.sh"

# VyOS prints exactly this when the candidate matches the running config. Both
# the pre-flight guard and the idempotence check key off it.
CLEAN = "No changes between working and active configurations"


def _script(set_lines, delete_lines):
    """Build the vbash script applied on the appliance."""
    body = [
        "#!/bin/vbash",
        # NOT `set -e` -- see the module docstring. This is the one place where
        # the usual shell hygiene is actively harmful.
        "source /opt/vyatta/etc/functions/script-template",
        "configure",
        "",
        "# GUARD: refuse to touch a candidate someone else is already editing,",
        "# because commit would ship their changes along with ours.",
        'if ! compare | grep -q "%s"; then' % CLEAN,
        '    echo "flamelet-vyos: REFUSING -- candidate config already has'
        ' uncommitted changes" >&2',
        "    compare >&2",
    ] + _leave(3) + [
        "fi",
        "",
    ]
    for line in delete_lines:
        body.append("delete %s" % line)
    for line in set_lines:
        body.append("set %s" % line)
    body += [
        "",
        "# Idempotence: an empty diff means every value was already in place, so",
        "# discard rather than commit. Committing nothing still bumps the config",
        "# revision and would make every run report a change.",
        'if compare | grep -q "%s"; then' % CLEAN,
        '    echo "flamelet-vyos: no changes"',
        "    discard",
    ] + _leave(0) + [
        "fi",
        "",
        "commit",
        "# save is NOT optional: without it the change is lost on reboot while",
        "# looking completely correct until then.",
        "save",
        'echo "flamelet-vyos: committed and saved"',
    ] + _leave(0) + [""]
    return "\n".join(body)


def _leave(code, indent="    "):
    """Leave config mode and end the script with a real exit status.

    ⚠️ `exit N` DOES NOT WORK HERE and fails in a thoroughly misleading way.
    script-template defines a shell FUNCTION called `exit` (it means "leave
    configuration mode"), which shadows the builtin and takes no numeric
    argument — so `exit 0` is parsed as configuration and the appliance answers
    `Invalid command: [0]`. Measured on VyOS 2026.08 rolling:

        exit 3          -> rc=127, "Invalid command: [3]"
        builtin exit 3  -> rc=3,   no error

    The shadowing also survives leaving config mode, so a plain `exit` earlier in
    the script does not restore the builtin: every status return needs `builtin`.

    Two statements, in order: bare `exit` to leave configuration mode cleanly,
    then `builtin exit` to bypass the function and return the real status. The
    script removes itself first so the caller needs no compound shell command —
    a `; rm -f ...; exit $?` tail is itself re-parsed by the VyOS CLI and was the
    original symptom here.
    """
    return [
        f"{indent}exit",
        f'{indent}rm -f "$0"',
        f"{indent}builtin exit {code}",
    ]


def add_vyos_ops(state, hosts, config, target_hosts=None, task="all"):
    """Apply VyOS configuration statements.

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname -> {"set": [...], "delete": [...]}
        target_hosts: list of Host objects to limit to (default: all)
        task: task name being run
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        host_config = config[host.name] or {}
        set_lines = list(host_config.get("set") or [])
        delete_lines = list(host_config.get("delete") or [])
        if not set_lines and not delete_lines:
            continue

        # Written as a file rather than passed inline. The statements contain
        # spaces and quoting that would otherwise be mangled twice over -- once
        # by the local shell and once by vbash -- and a half-escaped `set` line
        # on a router is not a failure mode worth risking for brevity.
        add_op(
            state,
            files.put,
            name=f"Stage VyOS config script on {host.name}",
            # StringIO, NOT a bare string. files.put treats a str src as a LOCAL
            # PATH and tries to open it, so passing the script content directly
            # fails with `OSError: No such file: #!/bin/vbash...` -- the error
            # quotes the first line of your script back at you as a filename,
            # which is confusing enough to be worth naming here.
            src=StringIO(_script(set_lines, delete_lines)),
            dest=SCRIPT,
            mode="0700",
            host=host,
        )

        add_op(
            state,
            server.shell,
            name=(
                f"Apply {len(set_lines)} set / {len(delete_lines)} delete "
                f"statement(s) on {host.name}"
            ),
            # vbash explicitly: the config functions are only defined there, and
            # the login shell cannot be assumed.
            # ONE command, no compound. A `; rc=$?; rm -f ...; exit $rc` tail
            # gets re-parsed by the VyOS CLI (`Invalid command: [0]`), so the
            # script cleans itself up instead and this stays a single word pair.
            commands=[f"vbash {SCRIPT}"],
            host=host,
        )
