"""OPNsense driver.

Chosen as the reference driver because its API is publicly documented, it runs
in a VM, and contributors can test against it without proprietary hardware.

The API shape, which the engine was designed around rather than the reverse:

    https://<host>/api/<module>/<controller>/<command>/[<params>]

    search*/get*   read          GET
    add*/set*/del* write         POST, and STAGED -- not live until applied
    reconfigure    apply         POST, commits the staged changes

That staged-then-commit behaviour is not an OPNsense quirk; it is common to
appliances, which is why `apply_path` lives in ResourceType rather than here.

⚠️ Endpoint paths are NOT guessable. Gateway groups, for example, live under
`routing/group_settings` and not the `routing/settings` that the sibling gateway
endpoints use. When adding a resource type, read the controller list on a real
box rather than inferring from a pattern -- guessing produced four 404s before
the correct path was found.
"""

from __future__ import annotations

from core.api.drivers.base import Driver, ResourceType

#: Fields OPNsense returns but nobody declares. Comparing them would report a
#: change on every run.
_COMPUTED = (
    "uuid",
    "status",
    "status_translated",
    "label_class",
    "interface_descr",
    "dynamic",
    "virtual",
    "gateway_interface",
    "delay",
    "stddev",
    "loss",
    "upstream",
    "if",
)


class OPNsenseDriver(Driver):
    name = "opnsense"

    resources = {
        # System > Gateways. `priority` is the tier for plain routing; failover
        # ordering is expressed by gateway GROUPS, below.
        "gateway": ResourceType(
            name="gateway",
            identity_field="name",
            list_path="routing/settings/searchGateway",
            add_path="routing/settings/addGateway",
            set_path="routing/settings/setGateway",
            del_path="routing/settings/delGateway",
            payload_root="gateway_item",
            ignore_fields=_COMPUTED,
            apply_path="routing/settings/reconfigure",
        ),
        # System > Gateways > Group. Note the different controller -- see the
        # module docstring.
        "gateway_group": ResourceType(
            name="gateway_group",
            identity_field="name",
            list_path="routing/group_settings/search",
            add_path="routing/group_settings/add",
            set_path="routing/group_settings/set",
            del_path="routing/group_settings/del",
            payload_root="gateway_group",
            ignore_fields=_COMPUTED,
            apply_path="routing/group_settings/reconfigure",
        ),
        # Services > Kea DHCP > reservations. This is the resource that a
        # file-rendering model cannot express on an appliance, and the reason
        # DHCP pins otherwise stay hand-edited and drift.
        "dhcp_reservation": ResourceType(
            name="dhcp_reservation",
            identity_field="hw_address",
            list_path="kea/dhcpv4/searchReservation",
            add_path="kea/dhcpv4/addReservation",
            set_path="kea/dhcpv4/setReservation",
            del_path="kea/dhcpv4/delReservation",
            payload_root="reservation",
            ignore_fields=_COMPUTED,
            apply_path="kea/service/reconfigure",
        ),
        # Unbound host overrides -- local names that must resolve regardless of
        # upstream DNS.
        "dns_host_override": ResourceType(
            name="dns_host_override",
            identity_field="hostname",
            list_path="unbound/settings/searchHostOverride",
            add_path="unbound/settings/addHostOverride",
            set_path="unbound/settings/setHostOverride",
            del_path="unbound/settings/delHostOverride",
            payload_root="host",
            ignore_fields=_COMPUTED,
            apply_path="unbound/service/reconfigure",
        ),
    }

    def extract_rows(self, response, rt):
        """OPNsense returns {"rows": [...]} for search*, and a bare list rarely.

        `total`/`rowCount` are pagination metadata and are ignored: every
        resource type here is small enough that the default page covers it. A
        driver managing thousands of rows would need to page, and that belongs
        here rather than in the engine.
        """
        if isinstance(response, dict):
            if "rows" in response:
                return response["rows"] or []
            # get*-style single-object responses
            root = response.get(rt.payload_root)
            if isinstance(root, dict):
                return [root]
        return response or []

    def set_path_for(self, rt, uuid: str) -> str:
        """Updates address the object by uuid in the PATH, not the body."""
        return f"{rt.set_path}/{uuid}"

    def del_path_for(self, rt, uuid: str) -> str:
        return f"{rt.del_path}/{uuid}"
