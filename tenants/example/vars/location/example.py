"""Location-specific configuration for example.com hosts."""

# Example monit configuration for gateway host
MONIT = {
    "gw.example.com": {
        "daemon": 120,
        "httpd_port": 2812,
        "httpd_password": "example-password",
        "checks": {
            "system": "check system gw.example.com\n  if memory usage > 75% then alert",
            "filesystem_root": "check filesystem rootfs with path /\n  if space usage > 90% then alert",
        },
    },
}

# Example WireGuard configuration for gateway
WIREGUARD = {
    "gw.example.com": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.1/24",
                "port": 51820,
                "private_key": "example-private-key-placeholder",
                "peers": [
                    {
                        "pubkey": "example-peer-public-key-placeholder",
                        "allowed_ips": ["10.50.0.0/24"],
                        "endpoint": "peer.example.com:51820",
                    }
                ],
            }
        }
    }
}
