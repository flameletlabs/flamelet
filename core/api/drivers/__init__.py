"""Driver registry.

Adding a driver should be: write the module, add one line here. If it ever
requires more, the core/driver split has leaked and the engine is the thing to
fix.
"""

from __future__ import annotations

from core.api.drivers.base import Driver, ResourceType
from core.api.drivers.opnsense import OPNsenseDriver

_DRIVERS = {d.name: d for d in (OPNsenseDriver,)}


def get_driver(name: str) -> Driver:
    try:
        return _DRIVERS[name]()
    except KeyError:
        known = ", ".join(sorted(_DRIVERS)) or "none"
        raise KeyError(f"unknown API driver {name!r} (available: {known})") from None


def available_drivers() -> list[str]:
    return sorted(_DRIVERS)


__all__ = ["Driver", "ResourceType", "get_driver", "available_drivers"]
