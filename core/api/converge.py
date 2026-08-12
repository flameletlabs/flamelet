"""Drive a driver + client to reach declared state, or report what would change.

    fetch  ->  plan  ->  (stop here when dry)  ->  write  ->  apply  ->  verify

VERIFY IS NOT OPTIONAL. An HTTP 200 with a plausible body is not evidence that a
change took effect -- it means the request was accepted. Appliances stage writes
and commit them separately, so "accepted" and "in effect" are genuinely
different claims. After applying, this re-reads and re-plans; a non-empty plan
at that point means the appliance did not do what it said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.api.client import ApiClient
from core.api.drivers.base import Driver
from core.api.reconcile import Plan, build_plan


@dataclass
class ConvergeResult:
    target: str
    resource_type: str
    plan: Plan
    applied: bool = False
    verified: Optional[bool] = None
    #: Populated when verification found the appliance disagreeing with itself.
    residual: Optional[Plan] = None
    errors: list = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.applied and not self.plan.empty

    def describe(self) -> str:
        summary = self.plan.summary()
        head = f"{self.target} {self.resource_type}: {summary}"
        if not self.applied:
            return f"{head} [dry]"
        if self.verified is False:
            residual = self.residual.summary()
            return f"{head} [APPLIED BUT NOT VERIFIED: {residual}]"
        return f"{head} [applied]"


def fetch_current(client: ApiClient, driver: Driver, type_name: str) -> list[dict]:
    rt = driver.resource(type_name)
    return driver.extract_rows(client.get(rt.list_path), rt)


def converge_resource_type(
    client: ApiClient,
    driver: Driver,
    type_name: str,
    desired: list[dict],
    *,
    target: str = "",
    dry: bool = True,
    prune: bool = False,
    verify: bool = True,
) -> ConvergeResult:
    """Reconcile one resource type on one appliance.

    dry defaults to True. A convergence tool that writes when you forgot to say
    so is worse than one that does nothing when you forgot to say apply.
    """
    rt = driver.resource(type_name)
    current = fetch_current(client, driver, type_name)
    plan = build_plan(
        resource_type=type_name,
        identity_field=rt.identity_field,
        desired=desired,
        current=current,
        ignore=rt.ignore_fields,
        prune=prune,
    )
    result = ConvergeResult(target=target, resource_type=type_name, plan=plan)

    if dry or plan.empty:
        return result

    for action in plan.actions:
        try:
            if action.verb == "create":
                client.post(rt.add_path, driver.wrap_payload(action.spec, rt))
            elif action.verb == "update":
                path = getattr(driver, "set_path_for", None)
                target_path = path(rt, action.uuid) if path else rt.set_path
                client.post(target_path, driver.wrap_payload(action.spec, rt))
            elif action.verb == "delete":
                path = getattr(driver, "del_path_for", None)
                target_path = path(rt, action.uuid) if path else rt.del_path
                client.post(target_path, {})
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            described = action.describe()
            result.errors.append(f"{described}: {exc}")

    # Commit. Without this the appliance holds staged changes that are invisible
    # to anything reading its live state.
    if rt.apply_path and not result.errors:
        try:
            client.post(rt.apply_path, {})
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"apply {rt.apply_path}: {exc}")

    result.applied = True

    if verify and not result.errors:
        residual = build_plan(
            resource_type=type_name,
            identity_field=rt.identity_field,
            desired=desired,
            current=fetch_current(client, driver, type_name),
            ignore=rt.ignore_fields,
            prune=prune,
        )
        result.verified = residual.empty
        if not residual.empty:
            result.residual = residual
    return result
