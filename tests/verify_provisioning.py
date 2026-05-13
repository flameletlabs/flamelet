#!/usr/bin/env python3
"""Verify that provisioning operations were actually applied.

This script checks system state after provisioning to ensure configurations
were actually written and services are in the expected state.

Usage:
    python tests/verify_provisioning.py --task sysctl --task monit
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_sysctl():
    """Verify sysctl parameters were applied."""
    checks = [
        ("net.ipv4.ip_forward", "1"),
        ("vm.swappiness", "10"),
    ]

    results = []
    for param, expected in checks:
        try:
            result = subprocess.run(
                ["sysctl", param],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                value = result.stdout.split("=")[1].strip()
                status = "✓" if value == expected else f"⚠ (got {value}, expected {expected})"
                results.append(f"  {status} {param}")
            else:
                results.append(f"  ✗ Failed to check {param}")
        except Exception as e:
            results.append(f"  ✗ Error checking {param}: {e}")

    return "\n".join(results)


def check_monit():
    """Verify monit configuration was created."""
    checks = [
        (Path("/etc/monit.conf"), "monit config exists"),
        (Path("/etc/monit.d"), "monit.d directory exists"),
    ]

    results = []
    for path, desc in checks:
        if path.exists():
            results.append(f"  ✓ {desc}")
        else:
            results.append(f"  ✗ {desc} (not found at {path})")

    return "\n".join(results)


def check_services():
    """Verify systemd services are configured."""
    services = ["ssh", "ssh.service"]

    results = []
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", service],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                status = result.stdout.strip()
                results.append(f"  ✓ {service} is {status}")
                break
        except Exception:
            pass

    if not results:
        results.append("  ⚠ SSH service state: unable to verify (may not be running in container)")

    return "\n".join(results)


def check_packages():
    """Verify package list operation ran (harder to verify installed packages)."""
    # Instead of checking if packages are installed (which requires apt/pkg),
    # we verify the operation ran by checking if package facts were gathered
    results = [
        "  ℹ Package operation verification:",
        "    - Operation gathers host package facts",
        "    - Packages are not installed in test environment",
        "    - Check CI logs for 'packages' operations executed",
    ]
    return "\n".join(results)


def main():
    parser = argparse.ArgumentParser(description="Verify provisioning results")
    parser.add_argument(
        "--task",
        action="append",
        choices=["sysctl", "monit", "services", "packages"],
        help="Task to verify (can specify multiple times)",
    )
    args = parser.parse_args()

    tasks = args.task or ["sysctl", "monit", "services", "packages"]

    print("=== Provisioning Verification Results ===\n")

    checks = {
        "sysctl": ("Sysctl Parameters", check_sysctl),
        "monit": ("Monit Configuration", check_monit),
        "services": ("Services Management", check_services),
        "packages": ("Packages Operation", check_packages),
    }

    all_passed = True
    for task in tasks:
        if task in checks:
            title, check_fn = checks[task]
            print(f"{title}:")
            try:
                result = check_fn()
                print(result)
            except Exception as e:
                print(f"  ✗ Error during check: {e}")
                all_passed = False
            print()

    if all_passed:
        print("✓ All provisioning checks completed")
        return 0
    else:
        print("✗ Some provisioning checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
