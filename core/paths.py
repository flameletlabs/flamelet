"""Flexible path discovery for framework and tenants."""

import os
from pathlib import Path


def find_project_root(start_path=None):
    """Find framework project root using multiple strategies.

    Strategies (in order):
    1. FRAMEWORK_ROOT environment variable
    2. Relative path from calling script (../../ for tenants/*/run.py)
    3. Current working directory
    4. Search upward for core/ directory
    5. XDG install location (~/.local/share/flamelet/)

    Args:
        start_path: Starting path for search (default: script directory)

    Returns:
        Path object pointing to framework root
    """
    # Strategy 1: Environment variable
    if "FRAMEWORK_ROOT" in os.environ:
        root = Path(os.environ["FRAMEWORK_ROOT"]).resolve()
        if (root / "core").exists():
            return root

    # Strategy 2: Relative to calling script (for tenants/*/run.py)
    if start_path is None:
        import inspect
        frame = inspect.currentframe().f_back
        start_path = Path(frame.f_globals["__file__"]).parent

    start_path = Path(start_path).resolve()
    # Try ../.. for tenants/*/run.py -> framework/
    candidate = start_path.parent.parent.parent
    if (candidate / "core").exists():
        return candidate

    # Strategy 3: Current working directory
    if (Path.cwd() / "core").exists():
        return Path.cwd()

    # Strategy 4: Search upward
    current = start_path
    for _ in range(10):  # Limit search depth
        if (current / "core").exists():
            return current
        current = current.parent
        if current == current.parent:  # Reached filesystem root
            break

    # Strategy 5: XDG install location
    xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    xdg_framework = xdg_data_home / "flamelet"
    if (xdg_framework / "core").exists():
        return xdg_framework

    raise RuntimeError(
        "Cannot find framework root. Set FRAMEWORK_ROOT environment variable, "
        "ensure core/ directory exists in parent directories, or run install.sh"
    )


def setup_imports(start_path=None):
    """Configure sys.path to import framework modules.

    Usage in tenant run.py:
        from core.paths import setup_imports
        setup_imports()
        from core.operations.users import add_user_ops
    """
    import sys
    project_root = find_project_root(start_path)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root
