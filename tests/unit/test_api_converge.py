"""Converge tests: dry-run must not write, and apply must be verified.

These two properties are the ones whose failure is silent. A dry-run that writes
is a trust violation; an unverified apply reports success for a change that
never took effect.
"""

import pytest

from core.api.converge import converge_resource_type
from core.api.drivers import get_driver


class FakeClient:
    """Records every call. Reads come from a scripted list of states."""

    def __init__(self, states):
        self._states = list(states)
        self.gets = []
        self.posts = []

    def get(self, path):
        self.gets.append(path)
        state = self._states[0] if len(self._states) == 1 else self._states.pop(0)
        return {"rows": state}

    def post(self, path, payload=None):
        self.posts.append((path, payload))
        return {"result": "saved", "uuid": "new-uuid"}


DRIVER = get_driver("opnsense")
DESIRED = [{"name": "GW_A", "gateway": "192.0.2.1"}]


def test_dry_run_performs_no_writes_at_all():
    """The requirement, asserted rather than inspected."""
    client = FakeClient([[]])
    result = converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=True)
    assert client.posts == []
    assert not result.applied
    assert len(result.plan.of("create")) == 1
    assert "[dry]" in result.describe()


def test_dry_is_the_default():
    """Forgetting to say apply must not write."""
    client = FakeClient([[]])
    converge_resource_type(client, DRIVER, "gateway", DESIRED)
    assert client.posts == []


def test_apply_writes_then_commits():
    client = FakeClient([[], DESIRED])
    result = converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=False)
    paths = [p for p, _ in client.posts]
    assert "routing/settings/addGateway" in paths
    # The commit is a SEPARATE call; without it the appliance holds staged
    # changes that are invisible to anything reading live state.
    assert paths[-1] == "routing/settings/reconfigure"
    assert result.applied and result.verified is True


def test_payload_is_wrapped_in_the_drivers_envelope():
    client = FakeClient([[], DESIRED])
    converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=False)
    _, payload = client.posts[0]
    assert payload == {"gateway_item": {"name": "GW_A", "gateway": "192.0.2.1"}}


def test_update_addresses_the_object_by_uuid_in_the_path():
    current = [{"name": "GW_A", "gateway": "192.0.2.9", "uuid": "u-1"}]
    client = FakeClient([current, DESIRED])
    converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=False)
    assert client.posts[0][0] == "routing/settings/setGateway/u-1"


def test_verification_catches_an_appliance_that_did_not_apply():
    """The important one.

    The write returns 200 and the commit returns 200, but re-reading shows the
    old value. Without verification this reports success.
    """
    client = FakeClient([[], []])  # still empty after the write
    result = converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=False)
    assert result.applied
    assert result.verified is False
    assert result.residual is not None and not result.residual.empty
    assert "NOT VERIFIED" in result.describe()


def test_converged_state_makes_no_calls_and_reports_no_changes():
    client = FakeClient([DESIRED])
    result = converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=False)
    assert client.posts == []
    assert result.plan.empty
    assert not result.changed


def test_write_failure_is_reported_and_blocks_the_commit():
    """A failed write must not be followed by a commit that implies success."""

    class Failing(FakeClient):
        def post(self, path, payload=None):
            raise RuntimeError("boom")

    client = Failing([[], []])
    result = converge_resource_type(client, DRIVER, "gateway", DESIRED, dry=False)
    assert result.errors and "boom" in result.errors[0]
    assert result.verified is None  # not claimed either way


def test_unknown_resource_type_names_the_known_ones():
    client = FakeClient([[]])
    with pytest.raises(KeyError, match="gateway_group"):
        converge_resource_type(client, DRIVER, "nope", [], dry=True)
