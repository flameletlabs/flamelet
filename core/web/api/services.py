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
                    services.append(
                        {
                            "name": task_name,
                            "config_attr": config_attr,
                            "host_count": len(hosts),
                            "hosts": hosts,
                        }
                    )
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
                    services.append(
                        {
                            "name": task_name,
                            "config_attr": config_attr,
                        }
                    )
            except Exception:
                # Service config missing or load failed — skip it
                pass

    return sorted(services, key=lambda x: x["name"])


@router.get("/tenants/{tenant_name}/topology")
async def get_topology(tenant_name: str):
    """Get network topology graph (WireGuard spokes + AutoSSH tunnels)."""
    tenant_path = get_tenant_path(tenant_name)
    if not tenant_path:
        return {"error": f"Tenant '{tenant_name}' not found"}

    try:
        wireguard_config = load_service_config(tenant_path, "WIREGUARD")
        autossh_tunnels_config = load_service_config(tenant_path, "AUTOSSH_TUNNELS")
    except Exception as e:
        return {"error": f"Failed to load configs: {str(e)}"}

    # Optional tenant map of public endpoint name -> internal hostname, e.g.
    #     ENDPOINT_ALIASES = {"vpn.example.com": "gateway-01.internal"}
    # Absent is the normal case and means identity mapping, so a missing config
    # is {} rather than an error.
    try:
        endpoint_aliases = load_service_config(tenant_path, "ENDPOINT_ALIASES") or {}
    except Exception:
        endpoint_aliases = {}
    if not isinstance(endpoint_aliases, dict):
        endpoint_aliases = {}

    # Build pubkey → hostname map from peer comments (hub topology).
    # The hub is derived structurally — it is the node whose peers carry "spoke"
    # comments — so this works for any tenant regardless of naming.
    pubkey_to_host = {}
    hub_names = []

    for hub_name, hub_cfg in wireguard_config.items():
        if not isinstance(hub_cfg, dict) or "interfaces" not in hub_cfg:
            continue
        hub_peers = [
            peer
            for iface_cfg in hub_cfg.get("interfaces", {}).values()
            for peer in iface_cfg.get("peers", [])
        ]
        # A hub is a node that describes its peers as spokes. A spoke never does.
        if not any("spoke" in (peer.get("comment") or "") for peer in hub_peers):
            continue
        hub_names.append(hub_name)
        for peer in hub_peers:
            comment = peer.get("comment", "")
            pubkey = peer.get("pubkey")
            if not pubkey:
                continue
            if "spoke" in comment:
                # Comments read like "<hostname> spoke"
                pubkey_to_host[pubkey] = comment.split()[0]
            elif "uplink" not in comment:
                # Other hub peers map to the hub itself
                pubkey_to_host[pubkey] = hub_name

    # Build nodes
    nodes = []
    for hostname, wg_config in wireguard_config.items():
        if not isinstance(wg_config, dict) or "interfaces" not in wg_config:
            continue

        interfaces = {}
        for iface_name, iface_config in wg_config.get("interfaces", {}).items():
            addr = iface_config.get("address")
            if addr:
                interfaces[iface_name] = addr

        # Extract location from hostname (last segment after final dot)
        location = hostname.split(".")[-1] if "." in hostname else "unknown"

        nodes.append(
            {
                "id": hostname,
                "os": "unknown",  # Would need to cross-reference with inventory
                "location": location,
                "wg_interfaces": interfaces if interfaces else None,
            }
        )

    # Build WireGuard edges
    edges = []
    edge_ids = set()

    for hostname, wg_config in wireguard_config.items():
        if not isinstance(wg_config, dict) or "interfaces" not in wg_config:
            continue

        for iface_name, iface_config in wg_config.get("interfaces", {}).items():
            for peer in iface_config.get("peers", []):
                peer_pubkey = peer.get("pubkey")
                if not peer_pubkey:
                    continue

                # Look up which host this pubkey belongs to
                peer_host = pubkey_to_host.get(peer_pubkey)
                if not peer_host:
                    # Unknown peer: a spoke pointing at the hub. Only resolvable when
                    # exactly one hub was detected — with several, guessing which one
                    # would invent an edge, so the peer is skipped instead.
                    if len(hub_names) == 1:
                        peer_host = hub_names[0]
                    else:
                        continue

                # Skip self-loops (host can't be peer to itself)
                if peer_host == hostname:
                    continue

                edge_id = f"wg:{hostname}->{peer_host}"
                if edge_id in edge_ids:
                    continue
                edge_ids.add(edge_id)

                edges.append(
                    {
                        "id": edge_id,
                        "from": hostname,
                        "to": peer_host,
                        "type": "wireguard",
                        "interface": iface_name,
                        "direction": ("spoke-to-hub" if peer_host in hub_names
                                      else "peer-to-peer"),
                    }
                )

    # Build AutoSSH edges
    for tunnel_name, tunnel_config in autossh_tunnels_config.items():
        if not isinstance(tunnel_config, dict):
            continue

        deploy_to = tunnel_config.get("deploy_to")
        if not deploy_to:
            continue

        remote_host = tunnel_config.get("remote_host")
        local_port = tunnel_config.get("local_port")

        for from_host in deploy_to:
            # AutoSSH tunnel goes FROM deploy_to host TO remote_host. A tunnel's
            # remote_host is often the public gateway name while graph nodes are
            # keyed by internal hostname, so ENDPOINT_ALIASES reconciles the two.
            display_host = endpoint_aliases.get(remote_host, remote_host)

            edge_id = f"autossh:{tunnel_name}"
            if edge_id not in edge_ids:
                edge_ids.add(edge_id)
                edges.append(
                    {
                        "id": edge_id,
                        "from": from_host,
                        "to": display_host,
                        "type": "autossh",
                        "local_port": local_port,
                        "remote_host": remote_host,
                        "direction": "reverse-tunnel",
                    }
                )

    # Build location groups
    locations = {}
    for node in nodes:
        location = node["location"]
        if location not in locations:
            locations[location] = []
        locations[location].append(node["id"])

    return {
        "nodes": sorted(nodes, key=lambda x: x["id"]),
        "edges": sorted(edges, key=lambda x: x["id"]),
        "locations": locations,
    }
