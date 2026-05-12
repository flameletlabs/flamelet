"""Configuration loaders: 3-tier inheritance (all < location < host-specific)."""

import importlib.util
from pathlib import Path


def load_service_config(tenant_path: Path, attr_name: str) -> dict:
    """Load service configuration keyed by hostname: all.py < location/*.py < hosts/*.py.

    Args:
        tenant_path: Path to tenant directory (e.g., ~/.config/flamelet/tenants/flamelet-home/)
        attr_name: Attribute name to load (e.g., "WIREGUARD", "UNBOUND", "MONIT")

    Returns:
        dict mapping hostname → service config dict
    """
    vars_dir = tenant_path / "vars"
    config = {}

    # Load from all.py (global defaults)
    all_spec = importlib.util.spec_from_file_location("all_vars", vars_dir / "all.py")
    all_module = importlib.util.module_from_spec(all_spec)
    all_spec.loader.exec_module(all_module)
    all_config = getattr(all_module, attr_name, {})
    config.update(all_config)

    # Load from each location/*.py and merge per hostname
    location_dir = vars_dir / "location"
    if location_dir.exists():
        for location_file in location_dir.glob("*.py"):
            if location_file.name.startswith("_"):
                continue
            try:
                loc_spec = importlib.util.spec_from_file_location(
                    f"loc_{location_file.stem}", location_file
                )
                loc_module = importlib.util.module_from_spec(loc_spec)
                loc_spec.loader.exec_module(loc_module)
                loc_config = getattr(loc_module, attr_name, {})
                # Deep merge by hostname
                for hostname, host_config in loc_config.items():
                    if hostname not in config:
                        config[hostname] = {}
                    if isinstance(host_config, dict) and isinstance(config.get(hostname), dict):
                        config[hostname].update(host_config)
                    else:
                        config[hostname] = host_config
            except (ImportError, AttributeError):
                pass

    # Load from each hosts/*.py and merge per hostname
    hosts_dir = vars_dir / "hosts"
    if hosts_dir.exists():
        for host_file in hosts_dir.glob("*.py"):
            if host_file.name.startswith("_"):
                continue
            try:
                host_spec = importlib.util.spec_from_file_location(
                    f"host_{host_file.stem}", host_file
                )
                host_module = importlib.util.module_from_spec(host_spec)
                host_spec.loader.exec_module(host_module)
                host_config = getattr(host_module, attr_name, {})
                # Deep merge by hostname
                for hostname, hconfig in host_config.items():
                    if hostname not in config:
                        config[hostname] = {}
                    if isinstance(hconfig, dict) and isinstance(config.get(hostname), dict):
                        config[hostname].update(hconfig)
                    else:
                        config[hostname] = hconfig
            except (ImportError, AttributeError):
                pass

    return config


def load_packages_config(tenant_path: Path, host_name: str, os_key: str) -> dict:
    """Load packages configuration for a host: all < location < host-specific.

    Args:
        tenant_path: Path to tenant directory
        host_name: Full hostname (e.g., "virt.home", "nas-01.pangea")
        os_key: OS identifier (e.g., "Linux", "FreeBSD")

    Returns:
        dict like {os_key: [package_list]} with deduplication
    """
    vars_dir = tenant_path / "vars"
    config = []

    # Start with global defaults
    all_spec = importlib.util.spec_from_file_location("all_vars", vars_dir / "all.py")
    all_module = importlib.util.module_from_spec(all_spec)
    all_spec.loader.exec_module(all_module)
    config.extend(all_module.PACKAGES.get(os_key, []))

    # Add location overrides
    location = host_name.split(".")[-1]
    location_file = vars_dir / "location" / f"{location}.py"
    if location_file.exists():
        try:
            loc_spec = importlib.util.spec_from_file_location(f"loc_{location}", location_file)
            loc_module = importlib.util.module_from_spec(loc_spec)
            loc_spec.loader.exec_module(loc_module)
            pkg_list = getattr(loc_module, "PACKAGES", {}).get(os_key, [])
            if pkg_list:
                config.extend(pkg_list)
        except (ImportError, AttributeError):
            pass

    # Add host-specific overrides
    host_key = host_name.replace(".", "_").replace("-", "_")
    host_file = vars_dir / "hosts" / f"{host_key}.py"
    if host_file.exists():
        try:
            host_spec = importlib.util.spec_from_file_location(f"host_{host_key}", host_file)
            host_module = importlib.util.module_from_spec(host_spec)
            host_spec.loader.exec_module(host_module)
            pkg_list = getattr(host_module, "PACKAGES", {}).get(os_key, [])
            if pkg_list:
                config.extend(pkg_list)
        except (ImportError, AttributeError):
            pass

    return {os_key: list(set(config))} if config else {os_key: []}
