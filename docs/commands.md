# CLI Reference

## Synopsis

```
flamelet [OPTIONS] [COMMAND]
```

Flamelet requires a tenant (`-t`) for most commands. The exceptions are `sysinfo` and `update`, which operate on the flamelet installation itself.

## Commands

### ansible

Run an Ansible playbook for a tenant.

```bash
flamelet -t <tenant> ansible
```

Activates the tenant's virtual environment, optionally checks out the tenant repo (unless `-l` is set), and runs `ansible-playbook` with the inventory, playbook, and options defined in `config.sh`.

Pass additional Ansible arguments via `-o`:

```bash
flamelet -t <tenant> ansible -o "--tags users --limit debian"
```

### ansiblemodule

Run ad-hoc Ansible modules for a tenant.

```bash
flamelet -t <tenant> ansiblemodule -o "<ansible-arguments>"
```

Activates the tenant's virtual environment and runs `ansible` (not `ansible-playbook`) with the inventory and options from `config.sh`. Use `-o` to pass the module, target hosts, and arguments.

```bash
# Ping all hosts
flamelet -t mytenant ansiblemodule -o "all -m ping"

# Run a shell command on a specific group
flamelet -t mytenant ansiblemodule -o "webservers -m shell -a 'uptime'"
```

### installansible

Create or update the Ansible virtual environment for a tenant.

```bash
flamelet -t <tenant> installansible
```

This command:

1. Checks out the tenant repo (if `CFG_FLAMELET_TENANT_REPO` is set and not in offline mode)
2. Creates a Python virtual environment at `~/.flamelet/venv/<package>-<tenant>-<version>/`
3. Installs pip, the configured Ansible package and version, plus `jmespath` and `six`
4. Removes and installs Galaxy collections (if `CFG_ANSIBLE_GALAXY_COLLECTIONS_REMOVE` / `_INSTALL` are set)
5. Removes and installs Galaxy roles (if `CFG_ANSIBLE_GALAXY_ROLES_REMOVE` / `_INSTALL` are set)

Run this once when setting up a new tenant, or again when changing the Ansible version or Galaxy dependencies.

### checkout

Clone or update the tenant repository.

```bash
flamelet -t <tenant> checkout
```

If the tenant directory has no `.git` directory, clones the repo from `CFG_FLAMELET_TENANT_REPO`. Otherwise, fetches and resets to the configured branch (`CFG_FLAMELET_TENANT_BRANCH`, defaults to `origin/HEAD`).

This happens automatically before `ansible`, `ansiblemodule`, and `installansible` when a repo is configured and offline mode is not set.

### installremote

Install flamelet on a remote host via SSH.

```bash
flamelet -t <tenant> -r installremote
```

Copies the flamelet script and all library files to `~/.flamelet/bin/` on the remote SSH controller. Requires `CFG_SSH_CONTROLLER` to be set in `config.sh`.

After running this, you can use `flamelet -t <tenant> -r ansible` to execute playbooks on the remote host.

### nmap

Run network scans on configured subnets.

```bash
flamelet -t <tenant> nmap
```

Requires `CFG_NMAP_SUBNETS` (associative array of subnet names to IP ranges) in `config.sh`. Generates HTML reports using the nmap-bootstrap-xsl stylesheet and serves them via a local HTTP server on port 8100.

Per-subnet scan options can be set via `CFG_NMAP_SUBNETS_OPTS`, falling back to `CFG_NMAP_OPTS`.

### installdeps

Install system dependencies for flamelet.

```bash
flamelet installdeps
```

Detects the operating system and installs required packages using the appropriate package manager:

| OS             | Package Manager | Packages installed                                                                      |
| :------------- | :-------------- | :-------------------------------------------------------------------------------------- |
| Debian/Ubuntu  | apt-get         | bash, tree, rsync, git, tmux, ccze, ncdu, virt-what, python3, python3-venv, sshpass, nmap, xsltproc |
| RedHat/CentOS  | yum             | bash, hostname, tree, rsync, git, tmux, ccze, ncdu, python3                             |
| FreeBSD        | pkg             | bash, tree, rsync, git-lite, tmux, ccze, ncdu, wget, rust, nmap, libxslt                |
| OpenBSD        | pkg_add         | bash, tree, rsync, git, ncdu, python3, wget, rust, nmap, libxslt                        |

This command does not require a tenant.

### sysinfo

Show system information and check dependency status.

```bash
flamelet sysinfo
```

Reports the detected OS, Linux distribution (if applicable), and checks for the presence of: bash, python3, rsync, git, tmux, tree, ccze, ncdu. Also checks sudo availability.

This command does not require a tenant.

### update

Update flamelet itself.

```bash
flamelet update
```

Fetches the latest version from the flamelet GitHub repository and resets the local installation to match. If `~/.flamelet/bin/` is not yet a git repo, it re-clones from scratch.

This command does not require a tenant.

## Options

### Tenant

| Flag | Long | Description |
| :--- | :--- | :---------- |
| `-t` | `--tenant` | **Required for most commands.** Specifies which tenant configuration to use. Corresponds to the directory `~/.flamelet/tenant/flamelet-<name>/`. |

### Execution mode

| Flag | Long | Description |
| :--- | :--- | :---------- |
| `-r` | `--remote` | Run the command on the remote SSH controller instead of locally. The `-r` flag is stripped from the arguments before forwarding. |
| `-l` | `--offline` | Offline mode. Skips tenant repo checkout (git clone/pull). Use when the repo is already present or network is unavailable. |
| `-n` | `--dryrun` | Dry run mode. Non-destructive — makes no permanent changes. |

### Ansible passthrough

| Flag | Long | Description |
| :--- | :--- | :---------- |
| `-o` | `--option` | Pass additional options to the Ansible command. Quote the entire option string: `-o "--tags users --limit myhost"`. |

### Output control

| Flag | Long | Description |
| :--- | :--- | :---------- |
| `-v` | `--verbose` | Verbose output. Shows additional information during execution. |
| `-q` | `--quiet` | Quiet mode. Suppresses output. |
| `--force` | | Skip all user interaction. Implies "Yes" to all prompts. |
| `--loglevel` | | Set log level. One of: `FATAL`, `ERROR`, `WARN`, `INFO`, `NOTICE`, `DEBUG`, `ALL`, `OFF`. Default: `ERROR`. |
| `--logfile` | | Path to log file. Default: `~/logs/flamelet.log`. |

### Help

| Flag | Long | Description |
| :--- | :--- | :---------- |
| `-h` | `--help` | Display usage information and exit. |

## Usage Examples

```bash
# Run a playbook locally (offline mode, no repo checkout)
flamelet -t myproject -l ansible

# Run a playbook with specific tags
flamelet -t myproject -l ansible -o "--tags packages,users"

# Limit to specific hosts
flamelet -t myproject -l ansible -o "--limit webservers"

# Run a playbook remotely via SSH controller
flamelet -t myproject -r ansible

# Run ad-hoc ping on all hosts
flamelet -t myproject ansiblemodule -o "all -m ping"

# Set up a new tenant from scratch
flamelet -t myproject installansible

# Install flamelet on the remote controller
flamelet -t myproject -r installremote

# Check system dependencies
flamelet sysinfo

# Update flamelet
flamelet update
```
