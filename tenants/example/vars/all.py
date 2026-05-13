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

# NGINX — reverse proxy
NGINX = {
    "@local": {
        "upstreams": [
            {"name": "backend", "servers": ["127.0.0.1:8080"]},
        ],
        "servers": [
            {
                "server_name": "example.com",
                "listen": [80],
                "locations": [
                    {"path": "/", "proxy_pass": "http://backend"},
                ],
            }
        ],
    }
}

# POSTGRESQL — database server
POSTGRESQL = {
    "@local": {
        "version": "14",
        "databases": [{"name": "exampledb", "owner": "syseng"}],
        "users": [{"name": "syseng", "password": "example-password-hash"}],
    }
}

# UNBOUND — DNS resolver
UNBOUND = {
    "@local": {
        "listen_on": ["127.0.0.1"],
        "access_control": ["127.0.0.0/8 allow"],
        "local_data": [
            {"name": "example.local.", "type": "A", "value": "10.0.0.1"},
        ],
        "forward_zones": [
            {"name": ".", "addrs": ["1.1.1.1", "8.8.8.8"]},
        ],
    }
}

# OPENSMTPD — mail relay
OPENSMTPD = {
    "@local": {
        "mail_from": "noreply@example.com",
        "smtp_relay": "smtp+tls://alerts@smtp.example.com:587",
        "smtp_password": "example-app-password",
        "allowed_networks": ["10.0.0.0/24"],
    }
}

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

# REGISTRY — Docker registry
REGISTRY = {
    "@local": {
        "version": "2.8",
        "listen_port": 5000,
        "storage_path": "/data/registry",
        "storage_backend": "filesystem",
    }
}

# STORAGE — ZFS pools and datasets (Linux-compatible; will generate ops on @local)
STORAGE = {
    "@local": {
        "pools": [
            {
                "name": "tank",
                "devices": ["/dev/sdb", "/dev/sdc"],
                "type": "mirror",
                "ashift": 12,
                "compression": "lz4",
                "autotrim": True,
            }
        ],
        "datasets": [
            {
                "pool": "tank",
                "name": "data",
                "mountpoint": "/mnt/data",
                "quota": "100G",
                "compression": "lz4",
            }
        ],
    }
}

# AUTOSSH_TUNNELS — SSH reverse tunnels
AUTOSSH_TUNNELS = {
    "example-tunnel": {
        "remote_host": "gw.example.com",
        "remote_user": "autossh",
        "local_port": 2220,
        "local_target": "localhost:22",
        "deploy_to": ["@local"],
        "private_key": "/root/.ssh/id_rsa-autossh",
    }
}

# AUTOSSH_GATEWAY — SSH gateway authorized keys
AUTOSSH_GATEWAY = {
    "@local": {
        "authorized_keys": {
            "user": "autossh",
            "keys": [
                {
                    "comment": "example-client",
                    "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC example-placeholder",
                    "options": "no-pty,no-agent-forwarding",
                }
            ],
        }
    }
}

# K3S — Kubernetes
K3S = {
    "@local": {
        "mode": "server",
        "channel": "stable",
    }
}

# VIRTUALIZATION — VM management (FreeBSD-only at op level; config here for testing)
VIRTUALIZATION = {
    "@local": {
        "type": "bhyve",
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
