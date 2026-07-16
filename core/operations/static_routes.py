"""Manage static routes in rc.local for FreeBSD hosts."""

from pyinfra.operations import files


def add_static_routes_ops(state, host_state, routes_config):
    """
    Add static routes to rc.local (FreeBSD).

    Routes configuration format in host config:
    RC_LOCAL_ROUTES = {
        "hostname": {
            "routes": [
                {
                    "description": "Route description",
                    "command": "/sbin/route add -net 192.168.80.0/24 100.77.205.126",
                },
            ]
        }
    }
    """

    if not routes_config or not routes_config.get("routes"):
        return

    rc_local_path = "/etc/rc.local"

    # Add each route to rc.local (skips if already present)
    for route in routes_config.get("routes", []):
        description = route.get("description", "")
        command = route.get("command", "")

        if not command:
            continue

        # Add comment if provided
        if description:
            files.line(
                state,
                path=rc_local_path,
                line=f"# {description}",
                present=True,
            )

        # Add the route command
        files.line(
            state,
            path=rc_local_path,
            line=command,
            present=True,
        )
