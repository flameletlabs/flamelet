# Flamelet

Flamelet is a bash-based DevOps tool that wraps Ansible with multi-tenant support, virtual environment isolation, and remote execution. It lets you manage infrastructure across multiple projects and environments from a single installation.

Each tenant is a self-contained directory with its own configuration, inventory, playbook, and isolated Python virtual environment. You can switch between tenants with a single flag (`-t`), and run playbooks locally or remotely via an SSH controller.

## Use Cases

- **Local provisioning** — Configure the machine flamelet is running on (packages, users, services, config files)
- **Remote provisioning** — Run playbooks on remote infrastructure via an SSH controller, without installing Ansible on every target
- **Multi-OS fleet management** — Manage mixed fleets of Linux (Debian, RedHat), FreeBSD, and OpenBSD hosts from one tool
- **Air-gapped environments** — Operate in offline mode with pre-cached repos and venvs

## Prerequisites

- A Unix-like operating system: macOS, Linux, BSD. On Windows: WSL2 is preferred, but cygwin or msys also mostly work.
- `bash` v4 or greater
- `git`
- `curl`, `wget`, or `fetch` (for installation)
- `python3` with `venv` module (for Ansible virtual environments)

## Installation

Flamelet is installed by running one of the following commands in your terminal:

| Method    | Command                                                                                               |
| :-------- | :---------------------------------------------------------------------------------------------------- |
| **curl**  | `sh -c "$(curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |
| **wget**  | `sh -c "$(wget -O- https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"`   |
| **fetch** | `sh -c "$(fetch -o - https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |

This clones the flamelet repository to `~/.flamelet/bin/` and creates a symlink at `~/bin/flamelet`.

To install to a custom path, set the `FLAMELET` environment variable:

```bash
FLAMELET=/opt/flamelet sh install.sh
```

The installer also respects `REPO`, `REMOTE`, and `BRANCH` environment variables for custom source locations.

## First Run

The fastest way to get started is with the [example-local](https://github.com/flameletlabs/example-local) tenant:

```bash
# Clone the example tenant
git clone https://github.com/flameletlabs/example-local.git \
  ~/.flamelet/tenant/flamelet-example-local

# Install Ansible in an isolated virtual environment
flamelet -t example-local installansible

# Run the playbook on localhost
flamelet -t example-local -l ansible
```

The example playbook gathers system facts, installs a few common packages (`tree`, `curl`, `git`), and displays your current user. Once this works, you're ready to build your own tenant.

## Examples

- **[example-local](https://github.com/flameletlabs/example-local)** — Local provisioning. The simplest starting point: localhost-only inventory, self-contained playbook, no external dependencies.
- **[example-remote](https://github.com/flameletlabs/example-remote)** *(coming soon)* — Remote provisioning via SSH with multi-host inventory and Galaxy roles.

## Concepts

**Tenants** — A tenant is a self-contained configuration directory that flamelet manages. Each tenant lives at `~/.flamelet/tenant/flamelet-<name>/` and has its own `config.sh`, Ansible inventory, playbook, and virtual environment. Switch between tenants with `flamelet -t <name>`.

**config.sh** — The central configuration file for a tenant. It defines the tenant name, Ansible version, paths to inventory and playbook files, SSH controller settings, and Galaxy dependencies. See [Configuration](configuration.md) for the full variable reference.

**Virtual environments** — Flamelet creates an isolated Python virtual environment per tenant with the specified Ansible version. Venvs are stored at `~/.flamelet/venv/` and named `<package>-<tenant>-<version>`. This prevents version conflicts between tenants and keeps your system Python clean.

**Remote execution** — With the `-r` flag and an SSH controller configured, flamelet can run itself on a remote host. It SSHs to the controller and executes flamelet there, so the remote machine handles Ansible execution. See [Advanced](advanced.md) for details.

**Offline mode** — The `-l` flag skips git checkout operations, so flamelet can operate without network access once the tenant repo and venv are set up. Useful for air-gapped environments.

**Versioning** — Flamelet follows [Semantic Versioning](https://semver.org/). Check your installed version with `flamelet --version` or `flamelet version` (which also checks for updates). See the [Changelog](changelog.md) for release history.
