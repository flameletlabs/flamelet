# CLI Reference

## Synopsis

```
flamelet [OPTIONS] [COMMAND]
```

Flamelet requires a tenant (`-t`) for most commands. The exceptions are `sysinfo`, `update`, `version`, and `doctor` (without `-t`), which operate on the flamelet installation itself.

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

Run ad-hoc Ansible modules against your inventory without writing a playbook.

```bash
flamelet -t <tenant> ansiblemodule -o "<ansible-arguments>"
```

Activates the tenant's virtual environment and runs `ansible` (not `ansible-playbook`) with the inventory and options from `config.sh`. Output is one-line-per-host format. Use `-o` to pass the target hosts, module, and arguments.

#### Ping hosts

Check which hosts are reachable and have a working Python environment:

```bash
# Ping all hosts in inventory
flamelet -t mytenant ansiblemodule -o "all -m ping"

# Ping a specific group
flamelet -t mytenant ansiblemodule -o "debian -m ping"

# Ping a single host
flamelet -t mytenant ansiblemodule -o "web-01.example -m ping"
```

#### Run commands

Execute commands on remote hosts using the `command` module (default module) or `shell` (when you need pipes, redirects, or shell features):

```bash
# Check uptime on all hosts
flamelet -t mytenant ansiblemodule -o "all -m command -a 'uptime'"

# Disk usage on webservers
flamelet -t mytenant ansiblemodule -o "webservers -m command -a 'df -h'"

# Use shell module for pipes and redirects
flamelet -t mytenant ansiblemodule -o "all -m shell -a 'ps aux | grep nginx'"

# Check a service status
flamelet -t mytenant ansiblemodule -o "debian -m shell -a 'systemctl status nginx'"
```

#### Raw commands

The `raw` module executes commands directly over SSH without requiring Python on the remote host. Useful for bootstrapping fresh machines or managing minimal systems:

```bash
# Run on hosts that may not have Python installed
flamelet -t mytenant ansiblemodule -o "all -m raw -a 'uname -a'"

# Bootstrap Python on a fresh Debian host
flamelet -t mytenant ansiblemodule -o "newhost.example -m raw -a 'apt-get -y install python3'"

# Works on any host with SSH access, regardless of OS
flamelet -t mytenant ansiblemodule -o "freebsd -m raw -a 'pkg info'"
```

#### Other useful modules

Any Ansible module can be used with `ansiblemodule`:

```bash
# Gather facts
flamelet -t mytenant ansiblemodule -o "all -m setup -a 'filter=ansible_os_family'"

# Copy a file
flamelet -t mytenant ansiblemodule -o "webservers -m copy -a 'src=/tmp/config.conf dest=/etc/app/config.conf'"

# Install a package
flamelet -t mytenant ansiblemodule -o "debian -m apt -a 'name=htop state=present' --become"

# Manage services
flamelet -t mytenant ansiblemodule -o "webservers -m service -a 'name=nginx state=restarted' --become"
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

### doctor

Run health checks on flamelet and tenant configuration.

```bash
flamelet doctor
flamelet -t <tenant> doctor
```

Without a tenant, `doctor` runs global checks only:

- **Flamelet version** — checks if a newer version is available on GitHub
- **Stale virtual environments** — finds venvs under `~/.flamelet/venv/` that don't match any tenant's current `config.sh` (e.g. left over after a version bump), and offers to delete them

With a tenant (`-t`), it also runs:

- **Ansible version check** — queries PyPI for the latest stable release and the latest patch in your current major.minor series
- **Unused Galaxy collections** — scans tenant YAML files for FQCN references to each installed collection; reports collections with no matches
- **Unused Galaxy roles** — scans tenant YAML files for role references; reports roles with no matches

Useful flags:

| Flag | Effect |
| :--- | :----- |
| `-n` / `--dryrun` | Show what would be deleted without actually removing stale venvs |
| `--force` | Skip confirmation prompts (auto-yes for venv cleanup) |
| `-v` / `--verbose` | Show debug detail during checks |

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

Shows the current version, fetches the latest from the flamelet GitHub repository, and resets the local installation to match. After updating, it reports whether the version changed (e.g., `flamelet updated: 1.0.0 -> 1.1.0`) or if you were already up to date. If `~/.flamelet/bin/` is not yet a git repo, it re-clones from scratch.

This command does not require a tenant.

### version

Show the current flamelet version and check for updates.

```bash
flamelet version
```

Prints the local version, then fetches the latest version from GitHub and compares. If a newer version is available, it tells you to run `flamelet update`.

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

### Help and version

| Flag | Long | Description |
| :--- | :--- | :---------- |
| `-h` | `--help` | Display usage information and exit. |
| `-V` | `--version` | Display the current version and exit. |

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

# Check version and available updates
flamelet version

# Print version only
flamelet --version

# Update flamelet
flamelet update

# Run global health checks (version + stale venvs)
flamelet doctor

# Run full health checks for a tenant
flamelet -t myproject doctor

# Dry-run: see what stale venvs would be deleted
flamelet -n -t myproject doctor

# Auto-confirm venv cleanup
flamelet --force -t myproject doctor
```
