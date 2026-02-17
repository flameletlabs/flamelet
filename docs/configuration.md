# Configuration

## Directory Layout

Flamelet uses a single base directory at `~/.flamelet/` with the following structure:

```
~/.flamelet/
├── bin/                              # Flamelet installation (git repo)
│   ├── flamelet                      # Main script
│   └── share/flamelet/               # Library files (.bash)
├── venv/                             # Python virtual environments
│   └── ansible-myproject-9.12.0/     # One venv per tenant+version
├── tenant/                           # Tenant directories
│   └── flamelet-myproject/           # Tenant: "myproject"
│       ├── config.sh                 # Tenant configuration
│       ├── env.sh                    # Per-tenant environment (optional)
│       ├── ansible.cfg               # Ansible configuration
│       ├── inventory/                # Ansible inventory files
│       └── playbook.yml              # Ansible playbook
└── env.sh                            # Global environment (optional)
```

A symlink at `~/bin/flamelet` points to `~/.flamelet/bin/flamelet`.

## config.sh

Each tenant has a `config.sh` file at `~/.flamelet/tenant/flamelet-<name>/config.sh`. Flamelet sources this file before executing any tenant command. All variables are bash variables.

### Tenant identity

| Variable | Description |
| :------- | :---------- |
| `CFG_TENANT` | Tenant name. Should match the directory suffix (e.g., `myproject` for `flamelet-myproject/`). |

### Ansible settings

| Variable | Default | Description |
| :------- | :------ | :---------- |
| `CFG_ANSIBLE_PACKAGE` | `ansible` | Python package to install. Usually `ansible` or `ansible-core`. |
| `CFG_ANSIBLE_VERSION` | *(required)* | Version to install (e.g., `9.12.0`). Used by `installansible` to pin the Ansible version. |
| `CFG_ANSIBLE_CONFIG` | `/etc/ansible/ansible.cfg` | Path to `ansible.cfg`. Usually set to the tenant's own config file. |
| `CFG_ANSIBLE_INVENTORY` | *(required)* | Path to the inventory file or directory, relative to the tenant directory. |
| `CFG_ANSIBLE_PLAYBOOK` | *(required)* | Path to the playbook file, relative to the tenant directory. |
| `CFG_ANSIBLE_OPTIONS` | *(empty array)* | Additional options passed to every `ansible-playbook` invocation. |

### Repository settings

| Variable | Default | Description |
| :------- | :------ | :---------- |
| `CFG_FLAMELET_TENANT_REPO` | *(empty)* | Git URL of the tenant repository. If set, flamelet will clone/update the repo before running commands. Leave empty for locally-managed tenants. |
| `CFG_FLAMELET_TENANT_BRANCH` | `origin/HEAD` | Git branch to check out. |

### SSH and remote execution

| Variable | Description |
| :------- | :---------- |
| `CFG_SSH_CONTROLLER` | SSH destination for remote execution (e.g., `admin@controller.example`). Used with `-r` flag. |
| `CFG_SSH_OPTIONS` | Array of SSH options passed to `ssh` commands (e.g., `-o StrictHostKeyChecking=no`). |
| `CFG_SCP_OPTIONS` | Array of SCP options. Falls back to `CFG_SSH_OPTIONS` if not set. |
| `CFG_GIT_OPTIONS` | Options passed to `git` commands during checkout. |

### Galaxy dependencies

| Variable | Description |
| :------- | :---------- |
| `CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL` | Collections to install via `ansible-galaxy collection install`. |
| `CFG_ANSIBLE_GALAXY_COLLECTIONS_REMOVE` | Collections to remove before install (ensures clean state). |
| `CFG_ANSIBLE_GALAXY_ROLES_INSTALL` | Roles to install via `ansible-galaxy role install`. |
| `CFG_ANSIBLE_GALAXY_ROLES_REMOVE` | Roles to remove before install. |

### Network scanning

| Variable | Description |
| :------- | :---------- |
| `CFG_NMAP_SUBNETS` | Associative array mapping subnet names to IP ranges (e.g., `[lan]="192.168.1.0/24"`). |
| `CFG_NMAP_SUBNETS_OPTS` | Associative array mapping subnet names to nmap options. Falls back to `CFG_NMAP_OPTS`. |
| `CFG_NMAP_OPTS` | Default nmap options applied to all subnets (if per-subnet opts are not set). |

## Environment Files

Flamelet supports optional environment files for setting shell variables, aliases, or other shell customizations that shouldn't live in `config.sh`.

| File | Scope | Description |
| :--- | :---- | :---------- |
| `~/.flamelet/env.sh` | Global | Sourced for every tenant. Use for shared settings like SSH agent forwarding or PATH additions. |
| `~/.flamelet/tenant/flamelet-<name>/env.sh` | Per-tenant | Sourced after the global env. Use for tenant-specific environment variables. |

## Loading Order

When flamelet runs a tenant command, configuration is loaded in this order:

1. **config.sh** — `~/.flamelet/tenant/flamelet-<name>/config.sh`
2. **Global env.sh** — `~/.flamelet/env.sh` (if it exists)
3. **Tenant env.sh** — `~/.flamelet/tenant/flamelet-<name>/env.sh` (if it exists)

Later files can override variables set by earlier files. This lets you set defaults in `config.sh`, apply global overrides in the global env, and apply tenant-specific overrides last.

## Virtual Environment Naming

Each tenant gets an isolated Python virtual environment. The naming convention is:

```
~/.flamelet/venv/<CFG_ANSIBLE_PACKAGE>-<CFG_TENANT>-<CFG_ANSIBLE_VERSION>/
```

For example, a tenant named `myproject` using `ansible` version `9.12.0`:

```
~/.flamelet/venv/ansible-myproject-9.12.0/
```

This means you can have multiple tenants with different Ansible versions without conflicts.

## Example: Minimal config.sh (local)

A minimal configuration for local provisioning with no external repository:

```bash
CFG_TENANT="example-local"
CFG_ANSIBLE_PACKAGE="ansible"
CFG_ANSIBLE_VERSION="9.12.0"
CFG_ANSIBLE_CONFIG="${HOME}/.flamelet/tenant/flamelet-example-local/ansible.cfg"
CFG_ANSIBLE_INVENTORY="${HOME}/.flamelet/tenant/flamelet-example-local/inventory/hosts"
CFG_ANSIBLE_PLAYBOOK="${HOME}/.flamelet/tenant/flamelet-example-local/playbook.yml"
```

## Example: Full config.sh (remote with SSH controller)

A full configuration for remote provisioning with a git-managed tenant repo and Galaxy dependencies:

```bash
CFG_TENANT="myproject"
CFG_ANSIBLE_PACKAGE="ansible"
CFG_ANSIBLE_VERSION="9.12.0"

# Tenant repository
CFG_FLAMELET_TENANT_REPO="git@github.com:yourorg/your-tenant.git"
CFG_FLAMELET_TENANT_BRANCH="main"

# Ansible paths
CFG_ANSIBLE_CONFIG="${HOME}/.flamelet/tenant/flamelet-myproject/ansible.cfg"
CFG_ANSIBLE_INVENTORY="${HOME}/.flamelet/tenant/flamelet-myproject/inventory/"
CFG_ANSIBLE_PLAYBOOK="${HOME}/.flamelet/tenant/flamelet-myproject/playbook.yml"

# SSH controller for remote execution
CFG_SSH_CONTROLLER="admin@controller.example"
CFG_SSH_OPTIONS=(-o StrictHostKeyChecking=no -o ForwardAgent=yes)
CFG_SCP_OPTIONS=(-o StrictHostKeyChecking=no)

# Galaxy dependencies
CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL="community.general ansible.posix"
CFG_ANSIBLE_GALAXY_ROLES_INSTALL="geerlingguy.docker"

# Network scanning
declare -A CFG_NMAP_SUBNETS=(
    [office]="192.168.1.0/24"
    [servers]="10.0.0.0/24"
)
CFG_NMAP_OPTS="-sV -O"
```
