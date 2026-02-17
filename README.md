# flamelet

A DevOps tool for remote infrastructure management.

## Getting Started

### Prerequisites

- A Unix-like operating system: macOS, Linux, BSD. On Windows: WSL2 is preferred, but cygwin or msys also mostly work.
- `bash` should be installed
- `curl` or `wget` should be installed
- `git` should be installed

### Basic Installation

Flamelet is installed by running one of the following commands in your terminal. You can install this via the command-line with either `curl`, `wget` or another similar tool.

| Method    | Command                                                                                               |
| :-------- | :---------------------------------------------------------------------------------------------------- |
| **curl**      | `sh -c "$(curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |
| **wget**      | `sh -c "$(wget -O- https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"`   |
| **fetch**     | `sh -c "$(fetch -o - https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |

## Maintenance

```bash
flamelet version               # Check for updates
flamelet doctor                # Global health checks (stale venvs, version)
flamelet -t <tenant> doctor    # Full diagnostics (Ansible upgrades, unused Galaxy deps)
flamelet update                # Update flamelet
```

## Quick Start

Once flamelet is installed, try the [example-local](https://github.com/flameletlabs/example-local) tenant to see it in action:

1. Clone the example tenant:
   ```bash
   git clone https://github.com/flameletlabs/example-local.git \
     ~/.flamelet/tenant/flamelet-example-local
   ```

2. Install ansible in a virtual environment:
   ```bash
   flamelet -t example-local installansible
   ```

3. Run the playbook:
   ```bash
   flamelet -t example-local -l ansible
   ```

This will gather system facts, install a few common packages, and display your current user — all on localhost. See the [examples](examples/) directory for more.
