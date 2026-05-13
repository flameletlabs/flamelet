"""Host-specific configuration for docker.example.com (Debian build host)."""

# Docker configuration for the Debian build host
DOCKER = {
    "docker.example.com": {
        "storage_driver": "overlay2",
        "log_driver": "json-file",
        "log_opts": {"max-size": "10m", "max-file": "3"},
    }
}

# Additional packages for Debian Docker host
PACKAGES = {
    "Linux": ["docker-ce", "docker-compose-plugin", "buildkit"],
}
