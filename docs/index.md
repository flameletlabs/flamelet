# Welcome to flamelet

For full documentation visit [flameletlabs.github.io/flamelet](https://flameletlabs.github.io/flamelet/).

## Commands

* `flamelet new [dir-name]` - Create a new project.
* `flamelet serve` - Start the live-reloading docs server.
* `flamelet build` - Build the documentation site.
* `flamelet -h` - Print help message and exit.

## Project layout

    flamelet.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.


## What is Flamelet?
Flamelet is a DevOps tool for remote infrastructure management.
With Flamelet you can provision and update ...
Everything necessary for provisioning new infrastructure is already included in Flamelet. Furthermore functionality can be easily added with ...

## Use Cases
Provisioning new infrastructure remotely from scratch. Be it servers, including setting up users, sudo, shell, ...
Operating systems on computers, servers, 

## Prerequisites
- A Unix-like operating system: macOS, Linux, BSD. On Windows: WSL2 is preferred, but cygwin or msys also mostly work.
- `bash` should be installed
- `curl` or `wget` should be installed
- `git` should be installed


## Installation
Flamelet is installed by running one of the following commands in your terminal. You can install this via the command-line with either `curl`, `wget` or another similar tool.

| Method        | Command                                                                                               |
| :------------ | :---------------------------------------------------------------------------------------------------- |
| **curl**      | `sh -c "$(curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |
| **wget**      | `sh -c "$(wget -O- https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"`   |
| **fetch**     | `sh -c "$(fetch -o - https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |

## First Run

After installing flamelet, the fastest way to get started is with the [example-local](https://github.com/flameletlabs/example-local) tenant:

```bash
# Clone the example tenant
git clone https://github.com/flameletlabs/example-local.git \
  ~/.flamelet/tenant/flamelet-example-local

# Install ansible in a virtual environment
flamelet -t example-local installansible

# Run the playbook on localhost
flamelet -t example-local -l ansible
```

The example playbook gathers system facts, installs a few common packages (`tree`, `curl`, `git`), and displays your current user. Once this works, you're ready to build your own tenant.

## Examples

- **[example-local](https://github.com/flameletlabs/example-local)** — Local provisioning. The simplest starting point: localhost-only inventory, self-contained playbook, no external dependencies.
- **[example-remote](https://github.com/flameletlabs/example-remote)** *(coming soon)* — Remote provisioning via SSH with multi-host inventory and Galaxy roles.

## Concepts

**Tenants** — A tenant is a self-contained configuration directory that flamelet manages. Each tenant has its own `config.sh`, Ansible inventory, playbook, and virtual environment. You can manage multiple tenants (e.g., one per project or environment) and switch between them with `flamelet -t <name>`.

**config.sh** — The central configuration file for a tenant. It defines the tenant name, the Ansible version to use, paths to inventory/playbook files, SSH controller settings, and Galaxy dependencies. Flamelet reads this file to know how to set up and run Ansible for that tenant.

**Virtual environments** — Flamelet creates an isolated Python virtual environment per tenant with the specified Ansible version. This prevents version conflicts between tenants and keeps your system Python clean. Use `flamelet -t <name> installansible` to create or update the venv.

**Tags** — Ansible tags let you run only specific parts of a playbook. Pass them through flamelet with `flamelet -t <name> -l ansible -- --tags <tag>`. This is useful for running just the `packages` or `users` portion of a larger playbook.

**Offline mode** — Flamelet can operate without network access once the tenant repo and venv are set up. This is useful for air-gapped environments or when provisioning machines with limited connectivity.

## Adding Roles for further functionality


### Source for adding new roles
[Ansible Galaxy](https://galaxy.ansible.com/) prodes a vast amount of roles which can be integrated into Flamelet to extend its functionality. Simply go to [Ansible Galaxy](https://galaxy.ansible.com/), filter for "Roles" and look for what you need.

## Updating Flamelet

## Deleting Flamelet