"""Global defaults for all hosts in example home infrastructure."""

# OS-keyed package lists (installed on all hosts)
PACKAGES = {
    "FreeBSD": ["curl", "git", "htop", "sudo"],
    "OpenBSD": ["curl", "git", "htop"],
    "Linux": ["curl", "git", "htop"],
}

# SYSCTL — kernel parameters
SYSCTL = {
    "@local": {
        "net.ipv4.ip_forward": "1",
        "vm.swappiness": "10",
    }
}

# SERVICES — service management
SERVICES = {
    "@local": {
        "ssh": {"state": "started", "enabled": True},
    }
}

# MONIT — process monitoring
MONIT = {
    "@local": {
        "daemon": 120,
        "httpd_port": 2812,
        "httpd_password": "example-password",
        "checks": {
            "system": "check system @local\n  if memory usage > 75% then alert",
        },
    },
}

# WIREGUARD — VPN config (FreeBSD/OpenBSD-only at op level; config here for testing)
WIREGUARD = {
    "@local": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.1/24",
                "port": 51820,
                "private_key": "example-private-key-placeholder",
                "peers": [],
            }
        }
    }
}

# DOCKER — container runtime
DOCKER = {
    "@local": {
        "daemon": {
            "log-driver": "json-file",
            "log-opts": {"max-size": "10m", "max-file": "3"},
        },
    }
}

# NGINX — reverse proxy (not configured for @local; requires service management)
NGINX = {}

# POSTGRESQL — database server (not configured for @local; requires running postgres)
POSTGRESQL = {}

# UNBOUND — DNS resolver (not configured for @local; complex service requirements)
UNBOUND = {}

# OPENSMTPD — mail relay (not configured for @local)
OPENSMTPD = {}

# PF — BSD firewall (FreeBSD/OpenBSD-only at op level; config here for testing)
PF = {
    "@local": {
        "rules": "block in all\npass in on em0 proto tcp to port { 22 }\n",
    }
}

# NODE_EXPORTER — Prometheus node exporter
NODE_EXPORTER = {
    "@local": {
        "port": 9100,
    }
}

# PROMETHEUS — metrics server
PROMETHEUS = {
    "@local": {
        "listen_address": ":9090",
        "retention": "15d",
        "scrape_interval": "15s",
        "scrape_targets": [
            {"job_name": "node", "targets": ["localhost:9100"]},
        ],
    }
}

# REGISTRY — Docker registry (not configured for @local; requires docker)
REGISTRY = {}

# STORAGE — ZFS pools and datasets (not configured for @local; requires real devices)
STORAGE = {}

# AUTOSSH_TUNNELS — SSH reverse tunnels (not configured for @local; requires dedicated autossh user)
AUTOSSH_TUNNELS = {}

# AUTOSSH_GATEWAY — SSH gateway authorized keys (not configured for @local)
AUTOSSH_GATEWAY = {}

# K3S — Kubernetes (not configured for @local; complex service requirements)
K3S = {}

# BHYVE — FreeBSD bhyve VM management (FreeBSD-only)
BHYVE = {
    "@local": {
        "zvol_pool": "vm-pool",
        "bridges": [{"name": "vm-bridge0", "interface": "em0"}],
        "vms": [
            {
                "name": "example-vm",
                "vcpu": 2,
                "memory": "2G",
                "disk_size": "20G",
                "network": "vm-bridge0",
                "autostart": False,
            }
        ],
    }
}

# BASTILLE — FreeBSD Bastille jail management (FreeBSD-only)
BASTILLE = {
    "virt.example.com": {
        "release": "14.3-RELEASE",
        "bridge": "bridge10",
        "zfs_enable": True,
        "zfs_zpool": "zroot",
        "jails": [
            {
                "name": "db",
                "release": "14.3-RELEASE",
                "ip": "10.0.0.51/24",
                "gateway": "10.0.0.1",
                "thick": True,
                "static_mac": True,
                "sysvipc": True,
                "allow": {"raw_sockets": 1},
                "packages": ["mariadb1011-server", "python3"],
                "ssh": True,
                "autostart": True,
            },
            {
                "name": "app",
                "release": "14.3-RELEASE",
                "ip": "10.0.0.52/24",
                "gateway": "10.0.0.1",
                "thick": True,
                "static_mac": True,
                "packages": ["python3"],
                "ssh": True,
                "autostart": True,
            },
        ],
    }
}
