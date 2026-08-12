"""Turn declared desired state into the smallest set of API calls that reach it.

This is the part that makes API management IDEMPOTENT rather than a script that
POSTs blindly. It is deliberately pure: it takes the current state and the
desired state as plain data and returns a plan. No HTTP, no driver, no clock --
so it can be tested exhaustively without an appliance.

THE SHAPE
---------
    fetch current  ->  diff against desired  ->  Plan  ->  apply  ->  re-read

`--dry` stops after Plan. That is the whole definition, and it is defined ONCE,
here, rather than per operation: flamelet already has a case where --dry means
different things depending on the task, which makes "dry-run shows no changes"
an unsafe acceptance test. A second such case would be worse than the first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class FieldChange:
    name: str
    before: Any
    after: Any

    def __str__(self) -> str:  # pragma: no cover - display only
        before, after = self.before, self.after
        return f"{self.name}: {before!r} -> {after!r}"


@dataclass
class Action:
    """One create, update or delete against one resource."""

    verb: str  # "create" | "update" | "delete"
    resource_type: str
    identity: str
    spec: dict = field(default_factory=dict)
    uuid: Optional[str] = None
    changes: list[FieldChange] = field(default_factory=list)

    def describe(self) -> str:
        if self.verb == "update":
            detail = ", ".join(str(c) for c in self.changes)
            ident = self.identity
            return f"update {self.resource_type}[{ident}] ({detail})"
        verb, ident = self.verb, self.identity
        return f"{verb} {self.resource_type}[{ident}]"


@dataclass
class Plan:
    """What would change. Empty means converged."""

    actions: list[Action] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.actions

    def of(self, verb: str) -> list[Action]:
        return [a for a in self.actions if a.verb == verb]

    def summary(self) -> str:
        if self.empty:
            n_ok = len(self.unchanged)
            return f"no changes ({n_ok} resource(s) already correct)"
        counts = {v: len(self.of(v)) for v in ("create", "update", "delete") if self.of(v)}
        parts = ", ".join(f"{n} to {v}" for v, n in counts.items())
        n_ok = len(self.unchanged)
        return f"{parts}; {n_ok} already correct"


def _identity_of(spec: dict, identity_field: str) -> str:
    value = spec.get(identity_field)
    if value in (None, ""):
        raise ValueError(f"resource is missing its identity field {identity_field!r}")
    return str(value)


def diff_resource(
    desired: dict,
    current: dict,
    ignore: Iterable[str] = (),
) -> list[FieldChange]:
    """Compare ONLY the fields the caller declared.

    A appliance returns far more fields than anyone declares -- uuids, computed
    labels, display strings. Comparing everything would report a change on every
    run and make the whole feature useless, so absent-from-desired means
    "unmanaged", not "should be empty".
    """
    ignored = set(ignore)
    changes = []
    for key, want in desired.items():
        if key in ignored:
            continue
        have = current.get(key)
        # Appliances are loose about types: "1" and 1, "" and None. Compare as
        # strings so a cosmetic difference is not reported as drift forever.
        if _norm(have) != _norm(want):
            changes.append(FieldChange(key, have, want))
    return changes


def _norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def build_plan(
    resource_type: str,
    identity_field: str,
    desired: list[dict],
    current: list[dict],
    ignore: Iterable[str] = (),
    prune: bool = False,
) -> Plan:
    """Diff a whole resource type.

    prune=False by default, and that default is load-bearing: deleting anything
    the tenant did not declare would make flamelet destructive against an
    appliance it does not fully model. Removal must be asked for.
    """
    plan = Plan()
    by_identity = {}
    for item in current:
        try:
            by_identity[_identity_of(item, identity_field)] = item
        except ValueError:
            # A live object without the identity field cannot be matched. Skip
            # rather than crash: it is not ours to manage.
            continue

    declared: set[str] = set()
    for spec in desired:
        ident = _identity_of(spec, identity_field)
        declared.add(ident)
        existing = by_identity.get(ident)
        if existing is None:
            plan.actions.append(Action("create", resource_type, ident, spec=dict(spec)))
            continue
        changes = diff_resource(spec, existing, ignore=ignore)
        if changes:
            plan.actions.append(
                Action(
                    "update",
                    resource_type,
                    ident,
                    spec=dict(spec),
                    uuid=existing.get("uuid"),
                    changes=changes,
                )
            )
        else:
            plan.unchanged.append(ident)

    if prune:
        for ident, existing in by_identity.items():
            if ident not in declared:
                plan.actions.append(
                    Action("delete", resource_type, ident, uuid=existing.get("uuid"))
                )
    return plan
