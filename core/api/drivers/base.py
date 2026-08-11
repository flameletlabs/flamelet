"""What a driver must provide.

The core/driver split is the whole point of this feature: the engine handles
transport, diffing, dry-run and credentials, and a driver supplies only the
things that genuinely differ between appliances. If writing a second driver ever
requires touching the engine, the split is wrong and should be fixed there
rather than worked around here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResourceType:
    """One kind of thing a driver can manage.

    identity_field  which field makes two objects the same object. NOT the
                    uuid: uuids are assigned by the appliance, so they cannot
                    express desired state written by a human.
    ignore_fields   returned by the appliance but never declared -- uuids,
                    computed labels, display strings. Comparing them would
                    report drift on every run.
    """

    name: str
    identity_field: str
    list_path: str
    add_path: str
    set_path: str
    del_path: str
    payload_root: str
    rows_key: str = "rows"
    ignore_fields: tuple = ()
    #: Endpoint that commits staged changes. Appliances typically stage writes
    #: and require a separate apply; treating write and apply as one step leaves
    #: pending changes behind while reporting success.
    apply_path: Optional[str] = None


class Driver:
    """Base class. Subclasses declare `resources` and may override the hooks."""

    name: str = "base"
    resources: dict = {}

    def resource(self, type_name: str) -> ResourceType:
        try:
            return self.resources[type_name]
        except KeyError:
            known = ", ".join(sorted(self.resources)) or "none"
            raise KeyError(
                f"driver {self.name!r} has no resource type {type_name!r} (known: {known})"
            ) from None

    # -- hooks a driver may override -------------------------------------

    def extract_rows(self, response, rt: ResourceType) -> list:
        """Pull the list of objects out of a list/search response."""
        if isinstance(response, dict):
            return response.get(rt.rows_key) or []
        return response or []

    def wrap_payload(self, spec: dict, rt: ResourceType) -> dict:
        """Wrap a flat spec in whatever envelope the appliance expects."""
        return {rt.payload_root: dict(spec)}

    def uuid_of(self, obj: dict) -> Optional[str]:
        return obj.get("uuid")
