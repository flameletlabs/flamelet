"""Manage static routes in rc.local for FreeBSD hosts."""

from pyinfra.api.operation import add_op
from pyinfra.operations import files


def add_static_routes_ops(state, hosts, config, target_hosts=None, task="all"):
    """
    Add static routes to rc.local (FreeBSD).

    Routes configuration format in host config:
    RC_LOCAL_ROUTES = {
        "hostname": {
            "routes": [
                {
                    "description": "Route description",
                    "command": "/sbin/route add -net 10.40.0.0/24 100.64.0.14",
                },
            ]
        }
    }

    Args:
        state: pyinfra State object
        hosts: Inventory object
        config: dict mapping hostname -> routes config
        target_hosts: list of Host objects (default: all)
        task: "static-routes" or "all"

    NOTE (fixed 2026-08-06, found by the FH-33 drift audit): this operation had
    never been migrated to the (state, hosts, config, target_hosts, task)
    contract that every other operation uses. It still took the original
    three-argument form and indexed a single host's config directly.

    The consequence was much wider than a broken task. The registry filters this
    entry to ["FreeBSD"], and the dispatcher calls it with five arguments, so
    *any* flamelet run against *any* FreeBSD host aborted with

        add_static_routes_ops() takes 3 positional arguments but 5 were given

    before a single operation was generated -- whether or not that host declared
    RC_LOCAL_ROUTES at all (only virt.london does). Every FreeBSD host in the
    inventory was therefore unprovisionable, and because the traceback names
    static routes it read like a niche problem rather than a total outage.

    It also called files.line(state, ...) positionally, which pyinfra 3 does not
    accept; operations are queued through add_op(). That would have failed even
    once the signature was right.
    """
    targets = target_hosts if target_hosts else list(hosts)

    for host in targets:
        if host.name not in config:
            continue

        routes_config = config[host.name] or {}
        routes = routes_config.get("routes") or []
        if not routes:
            continue

        rc_local_path = "/etc/rc.local"

        for route in routes:
            description = route.get("description", "")
            command = route.get("command", "")

            if not command:
                continue

            if description:
                add_op(
                    state,
                    files.line,
                    name=f"Static route comment on {host.name}: {description}",
                    path=rc_local_path,
                    line=f"# {description}",
                    present=True,
                    host=host,
                )

            add_op(
                state,
                files.line,
                name=f"Static route on {host.name}: {command}",
                path=rc_local_path,
                line=command,
                present=True,
                host=host,
            )
