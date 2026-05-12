"""flamelet-home example tenant variables: SSH keys, passwords, user configs."""

from core.operations.users import BASH, SUDO_GROUP

# System groups to create (detail provided by tenant, not framework)
GROUPS = ["syseng", "keep"]

# Password for all shell users: example (sha-512)
# Generated with: mkpasswd --method=sha-512 <<< "example-password-123"
EXAMPLE_PASSWORD = "$6$JiB7s7.R6s7g9s7g$5G4h5I6j6K7l7M8m8N9n9O0o0P1p1Q2q2R3r3S4s4T5t5U6u6V7v7W8w8X9x9Y0y0"

# SSH keys per user (EXAMPLE KEYS - replace with your actual keys)
SYSENG_SSH_KEYS = [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vblnrMvyqCZ8v5zt3nKPh9qL3nL9pM8rK7sJ5tY6uQ3xR4sT5uU6vV7wW8xY9zE0fH1gI2jJ3kK4lL5mM6nN7oO8pP9qQ0rR1sS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC2dD3eE4fF5gG6hH7iI8jJ9kK0lL1mM2nN3oO4pP5qQ6rR7sS8tT9uU0vV1wW2xX3yY4zZ5aA6bB7cC8dD9eE0fF1gG2hH3iI4jJ5kK6lL7mM8nN9oO0pP1qQ2rR3sS4tT5uU6vV7wW8xX9yY0zZ admin@example.com",
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDKwvbnmLmyqDZ9w6au4oNPi9sM4oM0pN9rL8uJ6uZ7vR4yS5tU6vV7wW8xY9zF1gH2hI3jJ4kL5mM6nN7oO8pP9qQ0rR1sS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC2dD3eE4fF5gG6hH7iI8jJ9kK0lL1mM2nN3oO4pP5qQ6rR7sS8tT9uU0vV1wW2xX3yY4zZ5aA6bB7cC8dD9eE0fF1gG2hH3iI4jJ5kK6lL7mM8nN9oO0pP1qQ2rR3sS4tT5uU6vV7wW8xX9yY0zZ backup@example.com",
]

KEEP_SSH_KEYS = [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCxwvcnmLnyqDZ9w6bu4oPPi9tN4pN1qO9sM8vJ7vZ8wS5uT6vV7wW8xY9zG2hI3jJ4kL5mM6nN7oO8pP9qQ0rR1sS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC2dD3eE4fF5gG6hH7iI8jJ9kK0lL1mM2nN3oO4pP5qQ6rR7sS8tT9uU0vV1wW2xX3yY4zZ5aA6bB7cC8dD9eE0fF1gG2hH3iI4jJ5kK6lL7mM8nN9oO0pP1qQ2rR3sS4tT5uU6vV7wW8xX9yY0zZ demo@example.com",
]

# User configurations
USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": EXAMPLE_PASSWORD,
        "groups": SUDO_GROUP,  # Dict will be resolved per-host by add_users
        "shell": BASH,         # Dict will be resolved per-host by add_users
        "public_keys": SYSENG_SSH_KEYS,
    },
    "keep": {
        "comment": "Backup User",
        "password": EXAMPLE_PASSWORD,
        "groups": [],
        "shell": "/bin/sh",
        "public_keys": KEEP_SSH_KEYS,
    },
}
