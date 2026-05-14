"""Service configuration query endpoints."""

from fastapi import APIRouter
from core.paths import get_tenant_path
from core.tasks import TASK_REGISTRY
from core.tasks.loader import load_service_config

router = APIRouter()


@router.get("/tenants/{tenant_name}/services")
async def list_services(tenant_name: str):
    """List all configured services and which hosts have them."""
    tenant_path = get_tenant_path(tenant_name)
    if not tenant_path:
        return {"error": f"Tenant '{tenant_name}' not found"}

    services = []
    seen_attrs = set()

    # Iterate TASK_REGISTRY to enumerate all services
    for task_name, task_entries in TASK_REGISTRY.items():
        for entry in task_entries:
            config_attr = entry.config_attr

            # Skip special cases: users/sudo (no config_attr), packages (OS-keyed)
            if config_attr is None or entry.op_type == "packages":
                continue

            # Avoid duplicate entries for same config_attr (e.g., autossh has 2 entries)
            # Use config_attr as the unique key, but expose task_name-based service names
            service_key = (config_attr, task_name)
            if service_key in seen_attrs:
                continue
            seen_attrs.add(service_key)

            try:
                config = load_service_config(tenant_path, config_attr)
                hosts = sorted(config.keys()) if config else []

                if hosts:  # Only return services with at least one host
                    services.append({
                        "name": task_name,
                        "config_attr": config_attr,
                        "host_count": len(hosts),
                        "hosts": hosts,
                    })
            except Exception:
                # Service config missing or load failed — skip it
                pass

    return sorted(services, key=lambda x: -x["host_count"])


@router.get("/tenants/{tenant_name}/services/{service_name}")
async def get_service_detail(tenant_name: str, service_name: str):
    """Get detailed config summary for a specific service."""
    tenant_path = get_tenant_path(tenant_name)
    if not tenant_path:
        return {"error": f"Tenant '{tenant_name}' not found"}

    # Find config_attr for this service name
    config_attr = None
    for task_name, task_entries in TASK_REGISTRY.items():
        if task_name == service_name:
            for entry in task_entries:
                if entry.config_attr and entry.op_type != "packages":
                    config_attr = entry.config_attr
                    break
            break

    if not config_attr:
        return {"error": f"Service '{service_name}' not found or not queryable"}

    try:
        config = load_service_config(tenant_path, config_attr)
    except Exception as e:
        return {"error": f"Failed to load config: {str(e)}"}

    hosts_detail = []
    for hostname, host_config in config.items():
        config_keys = list(host_config.keys()) if isinstance(host_config, dict) else []

        # Count nested items (e.g., "checks" in monit config)
        check_count = None
        if "checks" in host_config and isinstance(host_config["checks"], dict):
            check_count = len(host_config["checks"])

        detail = {
            "hostname": hostname,
            "config_keys": config_keys,
        }
        if check_count is not None:
            detail["check_count"] = check_count

        hosts_detail.append(detail)

    return {
        "name": service_name,
        "config_attr": config_attr,
        "hosts": sorted(hosts_detail, key=lambda x: x["hostname"]),
    }


@router.get("/tenants/{tenant_name}/hosts/{hostname}/services")
async def get_host_services(tenant_name: str, hostname: str):
    """List all services configured on a specific host."""
    tenant_path = get_tenant_path(tenant_name)
    if not tenant_path:
        return {"error": f"Tenant '{tenant_name}' not found"}

    services = []
    seen_attrs = set()

    # Iterate TASK_REGISTRY and check if hostname is in each service's config
    for task_name, task_entries in TASK_REGISTRY.items():
        for entry in task_entries:
            config_attr = entry.config_attr

            # Skip special cases
            if config_attr is None or entry.op_type == "packages":
                continue

            # Avoid duplicates
            service_key = (config_attr, task_name)
            if service_key in seen_attrs:
                continue
            seen_attrs.add(service_key)

            try:
                config = load_service_config(tenant_path, config_attr)
                if hostname in config:
                    services.append({
                        "name": task_name,
                        "config_attr": config_attr,
                    })
            except Exception:
                # Service config missing or load failed — skip it
                pass

    return sorted(services, key=lambda x: x["name"])
