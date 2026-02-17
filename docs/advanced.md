# Advanced Features

## Remote Execution

Flamelet can run on a remote host via an SSH controller. This is useful when you have a dedicated provisioning server that runs Ansible against your infrastructure, and you want to trigger it from your local machine.

### How it works

1. You run `flamelet -t <tenant> -r ansible` on your local machine
2. Flamelet SSHs to the host defined in `CFG_SSH_CONTROLLER`
3. On the remote host, flamelet runs the same command without the `-r` flag
4. The remote host executes Ansible against your infrastructure

### Setup

**1. Configure the SSH controller in `config.sh`:**

```bash
CFG_SSH_CONTROLLER="admin@controller.example"
CFG_SSH_OPTIONS=(-o StrictHostKeyChecking=no -o ForwardAgent=yes)
CFG_SCP_OPTIONS=(-o StrictHostKeyChecking=no)
```

**2. Install flamelet on the remote host:**

```bash
flamelet -t myproject -r installremote
```

This copies the flamelet script and libraries to `~/.flamelet/bin/` on the remote controller.

**3. Set up the tenant on the remote host:**

The remote host needs its own tenant configuration. Either:

- Set `CFG_FLAMELET_TENANT_REPO` so the remote can clone the tenant repo, or
- Manually place the tenant directory at `~/.flamelet/tenant/flamelet-<name>/` on the remote

**4. Install Ansible on the remote host:**

```bash
flamelet -t myproject -r installansible
```

**5. Run playbooks remotely:**

```bash
flamelet -t myproject -r ansible
flamelet -t myproject -r ansible -o "--tags users --limit debian"
```

### How arguments are forwarded

When using `-r`, flamelet strips the `-r` flag from the arguments and forwards everything else to the remote flamelet via SSH. For example:

```bash
# Local command:
flamelet -t myproject -r -l ansible -o "--tags users"

# Becomes on remote:
flamelet -t myproject -l ansible -o "--tags users"
```

## Offline Mode

The `-l` (or `--offline`) flag tells flamelet to skip all git checkout operations. Use this when:

- The tenant repo is already cloned and you don't want to pull changes
- You're in an air-gapped environment with no network access
- You're iterating quickly on local changes and don't want git to overwrite them

```bash
# Run without checking out the repo
flamelet -t myproject -l ansible

# Install ansible without checkout
flamelet -t myproject -l installansible
```

For a fully offline setup:

1. Clone the tenant repo manually while you have network access
2. Run `flamelet -t <tenant> installansible` to create the venv
3. From then on, use `-l` for all commands

## Network Scanning with nmap

Flamelet includes an nmap wrapper that scans configured subnets and generates HTML reports.

### Configuration

In `config.sh`, define subnets as an associative array:

```bash
declare -A CFG_NMAP_SUBNETS=(
    [office]="192.168.1.0/24"
    [servers]="10.0.0.0/24"
    [dmz]="172.16.0.0/24"
)

# Default options for all subnets
CFG_NMAP_OPTS="-sV -O"

# Per-subnet overrides (optional)
declare -A CFG_NMAP_SUBNETS_OPTS=(
    [dmz]="-sV -O -Pn"
)
```

### Running scans

```bash
flamelet -t myproject nmap
```

This will:

1. Download the nmap-bootstrap-xsl stylesheet (cached at `/tmp/nmap-bootstrap.xsl`)
2. Run `sudo nmap` for each configured subnet
3. Generate per-subnet XML and HTML reports in `/tmp/nmap_reports/`
4. Create an `index.html` linking all reports
5. Start a Python HTTP server on port 8100 to serve the reports

Reports are accessible at `http://<host>:8100/index.html`.

## Makefile Shortcuts

For tenants you use frequently, a `Makefile` can simplify common operations:

```makefile
TENANT = myproject

.PHONY: run install checkout remote nmap

run:
	flamelet -t $(TENANT) -l ansible

install:
	flamelet -t $(TENANT) installansible

checkout:
	flamelet -t $(TENANT) checkout

remote:
	flamelet -t $(TENANT) -r ansible

nmap:
	flamelet -t $(TENANT) nmap

tags-%:
	flamelet -t $(TENANT) -l ansible -o "--tags $*"

limit-%:
	flamelet -t $(TENANT) -l ansible -o "--limit $*"
```

Usage:

```bash
make run                # Run the playbook
make remote             # Run remotely
make tags-users         # Run only the users tag
make limit-debian       # Limit to debian group
```

## Updating Flamelet

```bash
flamelet update
```

This fetches the latest version from the [flamelet GitHub repository](https://github.com/flameletlabs/flamelet) and resets the local installation. No tenant is required.

If you installed flamelet to a custom path, `cd` into that directory first and run `git pull` manually.

## Uninstalling Flamelet

To completely remove flamelet and all its data:

```bash
rm -rf ~/.flamelet ~/bin/flamelet
```

This removes:

- The flamelet installation (`~/.flamelet/bin/`)
- All virtual environments (`~/.flamelet/venv/`)
- All tenant directories (`~/.flamelet/tenant/`)
- The symlink (`~/bin/flamelet`)

To remove only a specific tenant's venv while keeping everything else:

```bash
rm -rf ~/.flamelet/venv/ansible-myproject-9.12.0
```

## Galaxy Roles and Collections

Flamelet manages Galaxy dependencies through `config.sh` variables. They are installed (or removed and reinstalled) every time you run `installansible`.

### Collections

```bash
# In config.sh
CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL="community.general ansible.posix community.docker"
CFG_ANSIBLE_GALAXY_COLLECTIONS_REMOVE="community.general ansible.posix community.docker"
```

### Roles

```bash
# In config.sh
CFG_ANSIBLE_GALAXY_ROLES_INSTALL="geerlingguy.docker geerlingguy.certbot"
CFG_ANSIBLE_GALAXY_ROLES_REMOVE="geerlingguy.docker geerlingguy.certbot"
```

The `_REMOVE` variables are processed first, ensuring a clean install. This is useful when upgrading to newer versions of roles or collections.

### Finding roles and collections

Browse [Ansible Galaxy](https://galaxy.ansible.com/) to discover roles and collections. Filter by "Roles" or "Collections" and check download counts and maintenance status before adding dependencies.
