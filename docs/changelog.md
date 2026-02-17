# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-02-17

### Added

- **`doctor` command** — run `flamelet doctor` for global health checks or `flamelet -t <tenant> doctor` for full tenant diagnostics
- **Stale venv cleanup** — detects virtual environments under `~/.flamelet/venv/` that no longer match any tenant's `config.sh` (e.g. leftover after version bumps), with interactive or `--force` deletion; respects `--dryrun`
- **Ansible version check** — queries PyPI for the latest stable release and the latest patch in the current major.minor series
- **Unused Galaxy collections** — scans tenant YAML files for FQCN references and reports collections with no matches
- **Unused Galaxy roles** — scans tenant YAML files for role references (strips version pins) and reports roles with no matches
- **MkDocs search** — enabled the built-in search plugin for the documentation site

### Fixed

- **Option parsing** — flags like `-o` now work in any position, including after the command name (e.g. `flamelet -t x ansiblemodule -o "all -m ping"` previously corrupted the options to `nse`)
- **Empty option guard** — `_ansible_()` and `_ansibleModule_()` no longer mangle an unset `-o` value

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

[1.1.0]: https://github.com/flameletlabs/flamelet/releases/tag/v1.1.0
[1.0.0]: https://github.com/flameletlabs/flamelet/releases/tag/v1.0.0
