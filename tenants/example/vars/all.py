"""Global defaults for all hosts in example home infrastructure."""

# OS-keyed package lists (installed on all hosts)
PACKAGES = {
    "FreeBSD": ["curl", "git", "htop", "sudo"],
    "OpenBSD": ["curl", "git", "htop"],
    "Linux": ["curl", "git", "htop"],
}

# Service configurations (empty by default, can be overridden by location or host)
MONIT = {}
WIREGUARD = {}
DOCKER = {}
SERVICES = {}
SYSCTL = {}
POSTGRESQL = {}
NGINX = {}
