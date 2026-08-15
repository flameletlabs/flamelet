"""Task registry: maps task names to operations and their config attributes."""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TaskEntry:
    """Maps a task to an operation function and its config attribute.

    os_families: Optional list of OS kernel strings this operation supports.
                 None = all OS families. Examples: ["Linux"], ["FreeBSD"],
                 ["FreeBSD", "OpenBSD"]. Uses pyinfra Kernel fact values.
    """

    op_func: Callable
    config_attr: Optional[str]
    op_type: str
    os_families: Optional[list[str]] = None


def _init_registry() -> dict[str, list[TaskEntry]]:
    """Build TASK_REGISTRY after all imports are available."""
    from core.operations.api_resources import add_api_resource_ops
    from core.operations.autossh import add_autossh_gateway_ops, add_autossh_ops
    from core.operations.bastille import add_bastille_ops
    from core.operations.bhyve import add_bhyve_ops
    from core.operations.debian_network import add_debian_network_ops
    from core.operations.dnsmasq import add_dnsmasq_ops
    from core.operations.docker import add_docker_ops
    from core.operations.files import add_file_ops
    from core.operations.gateway_netbird_routing import add_gateway_netbird_routing_ops
    from core.operations.k3s import add_k3s_ops
    from core.operations.monit import add_monit_ops
    from core.operations.netbird import add_netbird_ops
    from core.operations.nginx import add_nginx_ops
    from core.operations.node_exporter import add_node_exporter_ops
    from core.operations.opensmtpd import add_opensmtpd_ops
    from core.operations.openwrt_firewall import add_openwrt_firewall_ops
    from core.operations.package_update import add_package_update_ops
    from core.operations.packages import add_package_ops
    from core.operations.pf import add_pf_ops
    from core.operations.pf_gateway_routing import add_pf_gateway_routing_ops
    from core.operations.postgresql import add_postgresql_ops
    from core.operations.prometheus import add_prometheus_ops
    from core.operations.proxmox import add_proxmox_ops
    from core.operations.registry import add_registry_ops
    from core.operations.resolv_conf import add_resolv_conf_ops
    from core.operations.services import add_service_ops
    from core.operations.static_routes import add_static_routes_ops
    from core.operations.storage import add_storage_ops
    from core.operations.sudo import add_sudoers_ops
    from core.operations.sysctl import add_sysctl_ops, add_sysrc_ops
    from core.operations.unbound import add_unbound_ops
    from core.operations.users import add_user_ops
    from core.operations.vyos import add_vyos_ops
    from core.operations.watchcat import add_watchcat_ops
    from core.operations.wireguard import add_wireguard_ops

    return {
        "users": [TaskEntry(add_user_ops, None, "users")],
        "sudo": [TaskEntry(add_sudoers_ops, None, "sudo")],
        "packages": [TaskEntry(add_package_ops, "PACKAGES", "packages")],
        "package-update": [TaskEntry(add_package_update_ops, None, "no-config")],
        "sysctl": [TaskEntry(add_sysctl_ops, "SYSCTL", "standard")],
        # VyOS appliances. Not OS-gated on Kernel like sysrc: VyOS reports
        # Linux, so a kernel filter would not distinguish it from any other
        # Debian host. The gate is having a VYOS block at all, which is the
        # same "declared or skipped" rule every hostname-keyed task uses.
        "vyos": [TaskEntry(add_vyos_ops, "VYOS", "standard")],
        "sysrc": [TaskEntry(add_sysrc_ops, "SYSRC", "standard", ["FreeBSD", "OpenBSD"])],
        "services": [TaskEntry(add_service_ops, "SERVICES", "standard")],
        # Generic file shipping. The operation existed since the repo was
        # written but was never imported or registered, so it was unreachable
        # from the CLI -- which is why every script and unit file on the
        # gateways got there by hand. Wired up 2026-08-06 (FH-29).
        "files": [TaskEntry(add_file_ops, "FILES", "standard")],
        "api": [TaskEntry(add_api_resource_ops, "API_TARGETS", "api")],
        "autossh": [
            TaskEntry(add_autossh_ops, "AUTOSSH_TUNNELS", "autossh"),
            TaskEntry(add_autossh_gateway_ops, "AUTOSSH_GATEWAY", "autossh"),
        ],
        "wireguard": [
            TaskEntry(add_wireguard_ops, "WIREGUARD", "standard", ["FreeBSD", "OpenBSD", "Linux"])
        ],
        "netbird": [TaskEntry(add_netbird_ops, "NETBIRD", "standard", ["Linux"])],
        "gateway-netbird-routing": [
            TaskEntry(
                add_gateway_netbird_routing_ops, "GATEWAY_NETBIRD_ROUTING", "standard", ["Linux"]
            )
        ],
        "unbound": [TaskEntry(add_unbound_ops, "UNBOUND", "standard")],
        "resolv-conf": [
            TaskEntry(add_resolv_conf_ops, "RESOLV_CONF", "standard", ["FreeBSD", "OpenBSD"])
        ],
        "monit": [TaskEntry(add_monit_ops, "MONIT", "standard")],
        "opensmtpd": [TaskEntry(add_opensmtpd_ops, "OPENSMTPD", "standard")],
        "pf": [TaskEntry(add_pf_ops, "PF", "standard", ["FreeBSD", "OpenBSD"])],
        "pf_gateway_routing": [
            TaskEntry(
                add_pf_gateway_routing_ops, "PF_GATEWAY_ROUTING", "standard", ["FreeBSD", "OpenBSD"]
            )
        ],
        "dnsmasq": [TaskEntry(add_dnsmasq_ops, "DNSMASQ", "standard", ["FreeBSD", "Linux"])],
        "debian-network": [TaskEntry(add_debian_network_ops, "NETWORK", "standard", ["Linux"])],
        "openwrt-firewall": [
            TaskEntry(add_openwrt_firewall_ops, "OPENWRT_FIREWALL", "standard", ["Linux"])
        ],
        "watchcat": [TaskEntry(add_watchcat_ops, "WATCHCAT", "standard", ["Linux"])],
        "docker": [TaskEntry(add_docker_ops, "DOCKER", "standard", ["Linux"])],
        "node_exporter": [TaskEntry(add_node_exporter_ops, "NODE_EXPORTER", "standard")],
        "k3s": [TaskEntry(add_k3s_ops, "K3S", "standard", ["Linux"])],
        "bhyve": [TaskEntry(add_bhyve_ops, "BHYVE", "standard", ["FreeBSD"])],
        "bhyve-config": [TaskEntry(add_bhyve_ops, "BHYVE", "standard", ["FreeBSD"])],
        "bastille": [TaskEntry(add_bastille_ops, "BASTILLE", "standard", ["FreeBSD"])],
        "proxmox": [TaskEntry(add_proxmox_ops, "PROXMOX", "standard", ["Linux"])],
        "storage": [TaskEntry(add_storage_ops, "STORAGE", "standard", ["FreeBSD", "Linux"])],
        "nginx": [TaskEntry(add_nginx_ops, "NGINX", "standard")],
        "postgresql": [TaskEntry(add_postgresql_ops, "POSTGRESQL", "standard")],
        "prometheus": [TaskEntry(add_prometheus_ops, "PROMETHEUS", "standard")],
        "registry": [TaskEntry(add_registry_ops, "REGISTRY", "standard", ["Linux"])],
        "static-routes": [
            TaskEntry(add_static_routes_ops, "RC_LOCAL_ROUTES", "standard", ["FreeBSD"])
        ],
    }


TASK_REGISTRY = _init_registry()
