"""Tenant and host listing endpoints."""

from fastapi import APIRouter
from core.paths import get_tenants
from core.cli import load_tenant_inventory, load_tenant_hosts

router = APIRouter()


@router.get("/tenants")
async def list_tenants():
    """List all configured tenants."""
    tenants = get_tenants()
    result = []
    for name, path in tenants.items():
        try:
            inventory = load_tenant_inventory(path)
            host_count = len(list(inventory))
        except Exception:
            host_count = 0
        result.append({"name": name, "path": str(path), "host_count": host_count})
    return result


@router.get("/tenants/{tenant_name}/hosts")
async def list_hosts(tenant_name: str):
    """List hosts in a tenant."""
    from core.paths import get_tenant_path
    from pyinfra.facts.server import Kernel

    tenant_path = get_tenant_path(tenant_name)
    if not tenant_path:
        return {"error": f"Tenant '{tenant_name}' not found"}

    inventory = load_tenant_inventory(tenant_path)
    hosts = []

    for host in inventory:
        # Get groups
        groups = host.groups if hasattr(host, "groups") else []

        # Derive OS from groups
        os_name = "Unknown"
        for group in groups:
            if group.lower() == "linux":
                os_name = "Linux"
                break
            elif group.lower() == "freebsd":
                os_name = "FreeBSD"
                break
            elif group.lower() == "openbsd":
                os_name = "OpenBSD"
                break

        # Extract location from hostname (last segment after last dot)
        location = host.name.split(".")[-1] if "." in host.name else ""

        hosts.append({
            "name": host.name,
            "os": os_name,
            "location": location,
            "groups": list(groups)
        })

    return hosts


@router.get("/tenants/{tenant_name}/locations")
async def list_locations(tenant_name: str):
    """Return location metadata for a tenant, merged with live host details."""
    from core.paths import get_tenant_path
    import importlib.util
    import sys

    tenant_path = get_tenant_path(tenant_name)
    if not tenant_path:
        return {"error": f"Tenant '{tenant_name}' not found"}

    # Load LOCATIONS from vars/__init__.py
    vars_module_path = tenant_path / "vars" / "__init__.py"
    if not vars_module_path.exists():
        return {"error": f"Tenant '{tenant_name}' has no vars/__init__.py"}

    spec = importlib.util.spec_from_file_location(
        f"tenant_vars_{tenant_name}", vars_module_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    locations_meta = getattr(mod, "LOCATIONS", {})

    # Load hosts grouped by location
    inventory = load_tenant_inventory(tenant_path)
    location_hosts = {}
    for host in inventory:
        loc = host.name.split(".")[-1] if "." in host.name else ""
        if loc not in location_hosts:
            location_hosts[loc] = []

        # Get OS from groups
        os_name = "Unknown"
        groups_lower = [g.lower() for g in (host.groups if hasattr(host, "groups") else [])]
        if "freebsd" in groups_lower:
            os_name = "FreeBSD"
        elif "openbsd" in groups_lower:
            os_name = "OpenBSD"
        elif "openwrt" in groups_lower:
            os_name = "OpenWRT"
        elif "debian" in groups_lower:
            os_name = "Debian"
        elif "linux" in groups_lower:
            os_name = "Linux"

        location_hosts[loc].append({
            "name": host.name,
            "os": os_name,
        })

    result = []
    # Merge: include all locations from metadata + any from hostnames not in metadata
    all_locations = set(locations_meta.keys()) | set(location_hosts.keys())
    for loc in sorted(all_locations):
        meta = locations_meta.get(loc, {})
        hosts = location_hosts.get(loc, [])
        result.append({
            "name": loc,
            "display_name": meta.get("display_name", loc),
            "address": meta.get("address", ""),
            "lat": meta.get("lat"),
            "lon": meta.get("lon"),
            "host_count": len(hosts),
            "hosts": hosts,
        })

    return result
