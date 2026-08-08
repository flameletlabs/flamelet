"""Tests for the per-host dry-run summary and its exit code.

A dry run had no way to say "I did not measure this host", and several very
different outcomes all rendered as something a reader takes for good news:

    host never reached      dropped from the active-host list, so it printed
                            nothing at all
    every host unreachable  pyinfra raised "No hosts remaining!" and the command
                            died with a traceback
    no --diff               operation names with no status; grepping the output
                            for "would apply" returns 0, which reads CLEAN
    nothing to do           "no operations queued"

Only the last is good news. In a bulk sweep across many hosts all four looked
alike, and a tally built by grepping counted the failures as clean hosts.

These tests pin the distinction. They are deliberately about the WORDS and the
EXIT CODE, because those are the two things a calling script can act on.
"""

from core.runner import _print_dry_summary


class _Host:
    """Stand-in for a pyinfra Host; the summary only reads .name.

    Hashable on purpose -- failed hosts arrive as a set, so a fake that cannot
    go in one would not exercise the real call shape.
    """

    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, _Host) and other.name == self.name


def _host(name):
    return _Host(name)


class TestDryRunSummary:
    def test_unreachable_host_is_named_and_exits_non_zero(self, capsys):
        """The core regression: silence must not read as success."""
        good, bad = _host("reachable.example.com"), _host("unreachable.example.com")

        code = _print_dry_summary(
            [good, bad],
            failed_hosts={bad},
            stats={"reachable.example.com": {"would_apply": 3, "unchanged": 9, "errors": 0}},
            evaluated_drift=True,
        )

        out = capsys.readouterr().out
        assert code == 1, "an unreachable host must make the run exit non-zero"
        assert "unreachable.example.com: FAILED" in out
        assert "NOT evaluated" in out, "must say the host was not measured, not just that it failed"
        assert "reachable.example.com: 3 would apply, 9 unchanged" in out

    def test_every_host_reachable_and_clean_exits_zero(self, capsys):
        host = _host("host.example.com")

        code = _print_dry_summary(
            [host],
            failed_hosts=set(),
            stats={"host.example.com": {"would_apply": 0, "unchanged": 12, "errors": 0}},
            evaluated_drift=True,
        )

        out = capsys.readouterr().out
        assert code == 0
        assert "host.example.com: 0 would apply, 12 unchanged" in out
        assert "FAILED" not in out

    def test_without_diff_says_it_did_not_evaluate_drift(self, capsys):
        """Without --diff nothing is measured, and that must be stated outright.

        This is the case that previously produced output containing neither
        "would apply" nor "no changes", so a grep-based tally scored it clean.
        """
        host = _host("host.example.com")

        code = _print_dry_summary([host], failed_hosts=set(), stats=None, evaluated_drift=False)

        out = capsys.readouterr().out
        assert code == 0, "not evaluating drift is not itself a failure"
        assert "not evaluated for drift" in out
        assert "PLAN LISTING" in out
        assert "--diff" in out, "must name the flag that would evaluate drift"

    def test_errored_operations_are_surfaced_not_folded_into_unchanged(self, capsys):
        """An operation that threw is not an operation that had nothing to do."""
        host = _host("host.example.com")

        _print_dry_summary(
            [host],
            failed_hosts=set(),
            stats={"host.example.com": {"would_apply": 1, "unchanged": 2, "errors": 4}},
            evaluated_drift=True,
        )

        assert "4 ERRORED" in capsys.readouterr().out

    def test_reports_every_targeted_host_even_when_all_are_unreachable(self, capsys):
        """The all-hosts-down case used to be a bare traceback."""
        hosts = [_host("a.example.com"), _host("b.example.com")]

        code = _print_dry_summary(hosts, failed_hosts=set(hosts), stats=None, evaluated_drift=True)

        out = capsys.readouterr().out
        assert code == 1
        assert "a.example.com: FAILED" in out
        assert "b.example.com: FAILED" in out
        assert "0 of 2 host(s) evaluated" in out
