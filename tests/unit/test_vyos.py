"""VyOS operation.

The tests that matter here are not "does it emit a set line" -- they are the
three safety properties, because each one corresponds to a way this breaks a
live router, and all three are invisible in a passing deploy.
"""

from core.operations.vyos import CLEAN, _script
from core.tasks import TASK_REGISTRY


class TestRegistration:
    def test_vyos_task_registered(self):
        assert "vyos" in TASK_REGISTRY
        assert TASK_REGISTRY["vyos"][0].config_attr == "VYOS"


class TestScript:
    def test_set_and_delete_statements_are_emitted(self):
        s = _script(["service ssh port 22"], ["service telnet"])
        assert "set service ssh port 22" in s
        assert "delete service telnet" in s

    def test_deletes_run_before_sets(self):
        """Otherwise a delete can undo a set made in the same run."""
        s = _script(["service ssh port 22"], ["service ssh"])
        assert s.index("delete service ssh") < s.index("set service ssh port 22")

    def test_refuses_a_dirty_candidate(self):
        """commit applies the WHOLE candidate, so a pending change from someone
        else would be shipped by our deploy. The guard must abort, not commit."""
        s = _script(["service ssh port 22"], [])
        guard = s.split("configure", 1)[1].split("set service ssh")[0]
        assert CLEAN in guard
        assert "exit 3" in guard
        # and it must come BEFORE any statement is applied
        assert s.index("exit 3") < s.index("set service ssh port 22")

    def test_saves_after_commit(self):
        """commit without save is lost on reboot, silently, while looking fine."""
        s = _script(["service ssh port 22"], [])
        assert "\ncommit\n" in s
        assert s.index("\ncommit\n") < s.index("\nsave\n")

    def test_discards_when_nothing_changed(self):
        """set on an existing value is a no-op; committing an empty diff would
        bump the config revision and make every run look like a change."""
        s = _script(["service ssh port 22"], [])
        tail = s.split("set service ssh port 22", 1)[1]
        assert CLEAN in tail
        # Match the COMMAND (`\ncommit\n`), not the substring: the explanatory
        # comment above it contains the word "Committing", and asserting on the
        # bare substring found that comment instead and failed a correct script.
        assert tail.index("exit 0") < tail.index("\ncommit\n")

    def test_never_uses_set_dash_e(self):
        """⚠️ Inside script-template `set` IS the config command, so `set -e` is
        parsed as configuration rather than enabling errexit. This is the single
        easiest way to break the operation while looking like good practice."""
        s = _script(["service ssh port 22"], [])
        assert "set -e" not in s
        assert "set -euo" not in s

    def test_sources_the_template_before_configuring(self):
        s = _script(["service ssh port 22"], [])
        assert s.index("script-template") < s.index("\nconfigure\n")


class TestExitSemantics:
    """The single hardest-won detail in this operation.

    script-template defines a shell FUNCTION called `exit` (meaning "leave
    configuration mode") which shadows the builtin and rejects a numeric
    argument. Measured on VyOS 2026.08 rolling:

        exit 3          -> rc=127, "Invalid command: [3]"
        builtin exit 3  -> rc=3,   no error

    The shadowing survives leaving config mode, so every status return needs
    `builtin`. This is invisible in review and produced a deploy that reported
    "executed 0 commands" while looking like a permissions problem.
    """

    def test_status_returns_use_builtin(self):
        s = _script(["service ssh port 22"], [])
        for line in s.split("\n"):
            st = line.strip()
            if st.startswith("exit ") and st != "exit":
                raise AssertionError(f"bare `exit N` will be misparsed: {st!r}")
        assert "builtin exit 0" in s
        assert "builtin exit 3" in s

    def test_leaves_config_mode_before_returning_status(self):
        s = _script(["service ssh port 22"], [])
        tail = s.rsplit("builtin exit 0", 1)[0]
        assert tail.rstrip().endswith('rm -f "$0"')
        assert "\n    exit\n" in s

    def test_script_removes_itself(self):
        """So the caller needs no compound shell command — a `; rm -f ...` tail
        is itself re-parsed by the VyOS CLI, which was the original symptom."""
        assert 'rm -f "$0"' in _script(["service ssh port 22"], [])
