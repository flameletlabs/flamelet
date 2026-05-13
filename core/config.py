"""XDG-compliant configuration loading for flamelet."""

import os
from pathlib import Path


def get_config_path():
    """Return path to flamelet config file.

    Uses XDG Base Directory Specification:
    $XDG_CONFIG_HOME/flamelet/config.toml (default: ~/.config/flamelet/config.toml)
    """
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "flamelet" / "config.toml"


def load_config():
    """Load and parse flamelet config.toml.

    Returns dict with [framework] and [tenants] sections.
    Returns empty dict if config file doesn't exist.
    """
    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib
        except ModuleNotFoundError:
            raise RuntimeError("tomllib/tomli not available. Install with: pip install tomli")

    config_path = get_config_path()
    if not config_path.exists():
        return {}

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_tenant_path(tenant_name):
    """Resolve a registered tenant path from config.

    Args:
        tenant_name: Name of tenant (key under [tenants] section)

    Returns:
        Path object to tenant directory (absolute, expanded)

    Raises:
        KeyError if tenant not registered in config
    """
    config = load_config()
    tenants = config.get("tenants", {})

    if tenant_name not in tenants:
        raise KeyError(
            f"Tenant '{tenant_name}' not registered. Add to {get_config_path()} under [tenants]"
        )

    tenant_path = Path(tenants[tenant_name]).expanduser().resolve()
    if not tenant_path.exists():
        raise RuntimeError(f"Tenant path does not exist: {tenant_path}")

    return tenant_path
