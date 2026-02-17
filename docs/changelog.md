# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-02-17

First stable release.

### Added

- **Semantic versioning** — `VERSION` file as single source of truth, `--version` / `-V` flag, `version` command with remote update checking
- **Version-aware updates** — `flamelet update` now shows before/after versions
- **GitHub Actions release workflow** — automatically creates a GitHub Release on tag push
- **Installer version display** — `tools/install.sh` prints the installed version
- **Remote install includes VERSION** — `installremote` copies the VERSION file to the remote host
- **Ad-hoc Ansible modules** — `ansiblemodule` command for running ad-hoc Ansible modules (`ping`, `command`, `raw`, `shell`, etc.) without a playbook
- **Collection removal fix** — use `rm -rf` instead of `ansible-galaxy collection remove`, which does not exist
- **Multi-page documentation site** — full MkDocs Material site with CLI reference, configuration guide, usage patterns, and advanced features
- **Example tenant documentation** — `example-local` tenant with step-by-step instructions
- **`conf_*_custom` composition pattern** — documented approach for composable default/custom variable overrides

### Features carried from pre-release development

- Multi-tenant support with isolated configuration per tenant
- Per-tenant Python virtual environments with pinned Ansible versions
- Remote execution via SSH controller (`-r` flag)
- Offline mode for air-gapped environments (`-l` flag)
- Dry run mode (`-n` flag)
- Tenant repository checkout and branch tracking
- System dependency installation across Debian, RedHat, FreeBSD, and OpenBSD
- Network scanning with nmap and HTML report generation
- System info and dependency checking (`sysinfo`)
- Galaxy roles and collections management
- Configurable SSH, SCP, and git options
- Environment file loading (`env.sh` at global and tenant level)
- Flexible logging with configurable log levels and log files

[1.0.0]: https://github.com/flameletlabs/flamelet/releases/tag/v1.0.0
