"""Flexible path discovery for framework and tenants (XDG-compliant)."""

import os
from pathlib import Path


def find_framework_root(start_path=None):
    """Find flamelet framework root using multiple strategies.

    Strategies (in order of precedence):
    1. FRAMEWORK_ROOT environment variable
    2. XDG_DATA_HOME (default ~/.local/share/flamelet)
    3. Relative path from calling script (../../ for tenants/*/run.py)
    4. Current working directory
    5. Search upward for core/ directory

    Returns:
        Path object pointing to framework root
    """
    # Strategy 1: Environment variable (development/testing override)
    if "FRAMEWORK_ROOT" in os.environ:
        root = Path(os.environ["FRAMEWORK_ROOT"]).resolve()
        if (root / "core").exists():
            return root

    # Strategy 2: XDG installed location (curl installer uses this)
    xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    xdg_framework = xdg_data_home / "flamelet"
    if (xdg_framework / "core").exists():
        return xdg_framework

    # Strategy 3: Relative to calling script (for local development tenants/*/run.py)
    if start_path is None:
        import inspect
        frame = inspect.currentframe().f_back
        start_path = Path(frame.f_globals["__file__"]).parent

    start_path = Path(start_path).resolve()
    # Try ../../../ for ~/.config/flamelet/tenants/*/run.py -> ~/.local/share/flamelet/
    candidate = start_path.parent.parent.parent
    if (candidate / "core").exists():
        return candidate

    # Strategy 4: Current working directory
    if (Path.cwd() / "core").exists():
        return Path.cwd()

    # Strategy 5: Search upward
    current = start_path
    for _ in range(10):  # Limit search depth
        if (current / "core").exists():
            return current
        current = current.parent
        if current == current.parent:  # Reached filesystem root
            break

    raise RuntimeError(
        "Cannot find flamelet framework. Tried:\n"
        "  1. FRAMEWORK_ROOT environment variable\n"
        "  2. XDG_DATA_HOME/flamelet (~/.local/share/flamelet)\n"
        "  3. Relative paths from tenant directory\n"
        "  4. Current working directory\n"
        "  5. Parent directories\n\n"
        "Set FRAMEWORK_ROOT=/path/to/framework or install via:\n"
        "  curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/install.sh | bash"
    )


def find_tenant_path(tenant_name=None):
    """Find tenant configuration path using multiple strategies.

    Strategies (in order):
    1. TENANT_PATH environment variable (for overrides)
    2. XDG_CONFIG_HOME (default ~/.config/flamelet/tenants)
    3. Local src directory (for development)
    4. Current directory

    Args:
        tenant_name: Name of tenant to find (optional, for explicit lookup)

    Returns:
        Path object pointing to tenant root
    """
    # Strategy 1: Environment variable override
    if "TENANT_PATH" in os.environ:
        path = Path(os.environ["TENANT_PATH"]).resolve()
        if path.exists():
            return path

    # Strategy 2: XDG config location (standard installation)
    xdg_config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    xdg_tenant = xdg_config_home / "flamelet" / "tenants"
    if tenant_name:
        tenant_path = xdg_tenant / tenant_name
        if tenant_path.exists():
            return tenant_path
    elif xdg_tenant.exists():
        return xdg_tenant

    # Strategy 3: Relative path from tenant script location
    import inspect
    frame = inspect.currentframe().f_back
    script_path = Path(frame.f_globals["__file__"]).resolve()
    if "tenants" in script_path.parts:
        # Script is in tenants/*/run.py, return tenant root
        tenant_root = script_path.parent
        if tenant_root.exists():
            return tenant_root

    # Strategy 4: Current working directory
    if Path.cwd().exists():
        return Path.cwd()

    raise RuntimeError(
        f"Cannot find tenant configuration. Tried:\n"
        f"  1. TENANT_PATH environment variable\n"
        f"  2. XDG_CONFIG_HOME/flamelet/tenants (~/.config/flamelet/tenants)\n"
        f"  3. Local development paths (tenants/*/)\n"
        f"  4. Current working directory"
    )


# Backward compatibility alias
def find_project_root(start_path=None):
    """Deprecated: Use find_framework_root instead."""
    return find_framework_root(start_path)


def setup_imports(start_path=None):
    """Configure sys.path to import framework modules.

    Usage in tenant run.py:
        from core.paths import setup_imports
        setup_imports()
        from core.operations.users import add_user_ops

    Returns:
        Path object pointing to framework root
    """
    import sys
    framework_root = find_framework_root(start_path)
    if str(framework_root) not in sys.path:
        sys.path.insert(0, str(framework_root))
    return framework_root
