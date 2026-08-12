"""Reconciler tests.

The reconciler decides what gets written to a firewall, so its failure modes are
expensive: a false "no changes" leaves an appliance unconverged and silent, and a
false change rewrites something that was already correct.
"""

import pytest

from core.api.reconcile import build_plan, diff_resource

GW = dict(resource_type="gateway", identity_field="name")


def test_empty_desired_and_current_is_converged():
    plan = build_plan(**GW, desired=[], current=[])
    assert plan.empty
    assert "no changes" in plan.summary()


def test_missing_resource_is_created():
    plan = build_plan(**GW, desired=[{"name": "GW_A", "gateway": "192.0.2.1"}], current=[])
    assert len(plan.of("create")) == 1
    assert plan.of("create")[0].identity == "GW_A"


def test_identical_resource_is_left_alone():
    spec = {"name": "GW_A", "gateway": "192.0.2.1"}
    plan = build_plan(**GW, desired=[spec], current=[dict(spec, uuid="abc")])
    assert plan.empty
    assert plan.unchanged == ["GW_A"]


def test_changed_field_produces_an_update_naming_that_field():
    plan = build_plan(
        **GW,
        desired=[{"name": "GW_A", "gateway": "192.0.2.9"}],
        current=[{"name": "GW_A", "gateway": "192.0.2.1", "uuid": "abc"}],
    )
    updates = plan.of("update")
    assert len(updates) == 1
    assert updates[0].uuid == "abc"
    assert [c.name for c in updates[0].changes] == ["gateway"]
    assert updates[0].changes[0].before == "192.0.2.1"
    assert updates[0].changes[0].after == "192.0.2.9"


def test_undeclared_fields_returned_by_the_appliance_are_not_drift():
    """An appliance returns far more than anyone declares.

    If these counted, every run would report a change and the feature would be
    useless. Absent-from-desired means unmanaged, not "should be empty".
    """
    plan = build_plan(
        **GW,
        desired=[{"name": "GW_A", "gateway": "192.0.2.1"}],
        current=[
            {
                "name": "GW_A",
                "gateway": "192.0.2.1",
                "uuid": "abc",
                "status": "Online",
                "label_class": "fa fa-plug",
            }
        ],
    )
    assert plan.empty


def test_ignore_fields_are_excluded_even_when_declared():
    plan = build_plan(
        **GW,
        desired=[{"name": "GW_A", "status": "Offline"}],
        current=[{"name": "GW_A", "status": "Online"}],
        ignore=("status",),
    )
    assert plan.empty


@pytest.mark.parametrize(
    "have,want",
    [("1", 1), (1, "1"), (True, "1"), (False, "0"), (None, ""), ("", None)],
)
def test_loose_appliance_typing_is_not_reported_as_drift(have, want):
    """Appliances are loose about types: "1" and 1, "" and None.

    Treating those as differences would report permanent, unfixable drift --
    every run would rewrite the value and every next run would see it again.
    """
    assert diff_resource({"f": want}, {"f": have}) == []


def test_real_difference_still_detected_despite_normalisation():
    assert len(diff_resource({"f": "2"}, {"f": "1"})) == 1


def test_undeclared_resources_are_not_deleted_by_default():
    """prune=False is load-bearing.

    Deleting what the tenant did not declare would make flamelet destructive
    against an appliance it does not fully model.
    """
    plan = build_plan(**GW, desired=[], current=[{"name": "MANUAL", "uuid": "z"}])
    assert plan.empty
    assert plan.of("delete") == []


def test_prune_deletes_undeclared_resources_when_asked():
    plan = build_plan(**GW, desired=[], current=[{"name": "MANUAL", "uuid": "z"}], prune=True)
    assert len(plan.of("delete")) == 1
    assert plan.of("delete")[0].uuid == "z"


def test_live_object_without_identity_is_skipped_not_fatal():
    plan = build_plan(**GW, desired=[{"name": "GW_A"}], current=[{"uuid": "no-name"}])
    assert len(plan.of("create")) == 1


def test_desired_without_identity_is_an_error():
    with pytest.raises(ValueError, match="identity"):
        build_plan(**GW, desired=[{"gateway": "192.0.2.1"}], current=[])
