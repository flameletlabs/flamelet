"""Example home infrastructure variables: users, groups, shell configs."""

# System groups to create
GROUPS = ["syseng", "keep"]

# Location metadata for map visualization
LOCATIONS = {
    "london": {
        "display_name": "London, UK",
        "address": "City of London, London, EC2V 8RT, UK",
        "lat": 51.5155,
        "lon": -0.0922,
    },
    "newyork": {
        "display_name": "New York, US",
        "address": "Lower Manhattan, New York, NY 10004, US",
        "lat": 40.7074,
        "lon": -74.0113,
    },
}

# Example password hash (sha-512, from mkpasswd --method=sha-512 <<< "example-password-123")
EXAMPLE_PASSWORD = (
    "$6$rounds=4096$examplesalt$JiB7s7R6s7g9s7g5G4h5I6j6K7l7M8m8N9n9O0o0P1p1Q2q2R3r3S4s4T5t5U6u6"
)

# Example SSH public keys (placeholder format)
SYSENG_KEYS = [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vblnrMvyqCZ8v5zt3nKPh9qL3nL9pM8rK7sJ5tY6uQ3xR4sT5uU6vV7wW8xY9zE0fH1gI2jJ3kK4lL5mM6nN7oO8pP9qQ0rR1sS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC2dD3eE4fF5gG6hH7iI8jJ9kK0lL1mM2nN3oO4pP5qQ6rR7sS8tT9uU0vV1wW2xX3yY4zZ5aA6bB7cC8dD9eE0fF1gG2hH3iI4jJ5kK6lL7mM8nN9oO0pP1qQ2rR3sS4tT5uU6vV7wW8xX9yY0zZ syseng@example.com",
]

KEEP_KEYS = [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDKwvbnmLmyqDZ9w6au4oNPi9sM4oM0pN9rL8uJ6uZ7vR4yS5tU6vV7wW8xY9zF1gH2hI3jJ4kL5mM6nN7oO8pP9qQ0rR1sS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC2dD3eE4fF5gG6hH7iI8jJ9kK0lL1mM2nN3oO4pP5qQ6rR7sS8tT9uU0vV1wW2xX3yY4zZ5aA6bB7cC8dD9eE0fF1gG2hH3iI4jJ5kK6lL7mM8nN9oO0pP1qQ2rR3sS4tT5uU6vV7wW8xX9yY0zZ keep@example.com",
]

# Shell paths per OS
BASH = {
    "FreeBSD": "/usr/local/bin/bash",
    "OpenBSD": "/usr/local/bin/bash",
    "Linux": "/bin/bash",
}

# Sudo group per OS
SUDO_GROUP = {
    "FreeBSD": "wheel",
    "OpenBSD": "wheel",
    "Linux": "sudo",
}

# User configurations (detail provided by tenant, not framework)
USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": EXAMPLE_PASSWORD,
        "groups": SUDO_GROUP,  # Dict will be resolved per-host by add_users
        "shell": BASH,  # Dict will be resolved per-host by add_users
        "public_keys": SYSENG_KEYS,
    },
    "keep": {
        "comment": "Backup User",
        "password": EXAMPLE_PASSWORD,
        "groups": [],
        "shell": "/bin/sh",
        "public_keys": KEEP_KEYS,
    },
}
