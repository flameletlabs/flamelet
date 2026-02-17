# Usage Patterns

This page covers common patterns for organizing Ansible inventories, playbooks, and variables when using flamelet.

## Inventory Organization

Inventories live in the tenant's `inventory/` directory. You can use a single `hosts` file or split hosts across multiple files in the directory.

### Group by OS

Organize hosts by operating system so you can target OS-specific tasks:

```ini
[debian]
web-01.example
web-02.example
db-01.example

[freebsd]
firewall-01.example
jail-host-01.example

[openbsd]
gateway-01.example
```

### Group by function

Overlay functional groups on top of OS groups:

```ini
[docker]
web-01.example
web-02.example

[k3s]
k8s-01.example
k8s-02.example
k8s-03.example

[monitoring]
monitor-01.example

[backup]
backup-01.example
```

### Nested children groups

Use `[group:children]` to compose larger groups:

```ini
[linux:children]
debian
redhat

[all_servers:children]
linux
freebsd
openbsd
```

### Per-host SSH overrides

Set connection parameters per host when defaults don't apply:

```ini
[servers]
server-01.example
server-02.example ansible_host=10.0.0.5 ansible_ssh_user=root
server-03.example ansible_connection=local
legacy-box.example ansible_ssh_user=admin ansible_port=2222
```

### Host ranges

Use range patterns for numbered hosts:

```ini
[webservers]
web-[01:04].example

[databases]
db-[01:02].example
```

### Complete example inventory

```ini
# inventory/hosts

[debian]
web-01.example
web-02.example
db-01.example
monitor-01.example

[freebsd]
firewall-01.example
jail-host-01.example

[openbsd]
gateway-01.example

[docker]
web-01.example
web-02.example

[k3s]
k8s-[01:03].example

[monitoring]
monitor-01.example

[linux:children]
debian

[all_servers:children]
linux
freebsd
openbsd
```

## Playbook Patterns

### Roles with tags and OS conditionals

Structure your playbook with roles that are tagged and conditionally applied by OS:

```yaml
---
- hosts: all
  become: true
  gather_facts: true

  roles:
    - role: packages
      tags: packages

    - role: users
      tags: users

    - role: ssh
      tags: ssh

    - role: docker
      tags: docker
      when: "'docker' in group_names"

    - role: monitoring
      tags: monitoring
      when: "'monitoring' in group_names"
```

### The conf_* variable pattern

A common pattern is to define configuration changes as data in `group_vars`, then apply them with generic tasks. This keeps roles reusable and moves the specifics into variables.

**In `group_vars/all`:**

```yaml
conf_lineinfile:
  - path: /etc/ssh/sshd_config
    regexp: "^PermitRootLogin"
    line: "PermitRootLogin prohibit-password"
    notify: restart sshd

conf_copy:
  - src: files/motd
    dest: /etc/motd
    mode: "0644"

conf_blockinfile:
  - path: /etc/security/limits.conf
    block: |
      * soft nofile 65536
      * hard nofile 65536
```

**In a role's tasks:**

```yaml
- name: Apply lineinfile configurations
  ansible.builtin.lineinfile:
    path: "{{ item.path }}"
    regexp: "{{ item.regexp }}"
    line: "{{ item.line }}"
  loop: "{{ conf_lineinfile | default([]) }}"
  tags: lineinfile
  notify: "{{ item.notify | default(omit) }}"

- name: Apply copy configurations
  ansible.builtin.copy:
    src: "{{ item.src }}"
    dest: "{{ item.dest }}"
    mode: "{{ item.mode | default('0644') }}"
  loop: "{{ conf_copy | default([]) }}"
  tags: copy
```

Other common `conf_*` variables follow the same pattern:

| Variable | Ansible module | Use case |
| :------- | :------------- | :------- |
| `conf_lineinfile` | `lineinfile` | Single-line edits in config files |
| `conf_blockinfile` | `blockinfile` | Multi-line block insertions |
| `conf_copy` | `copy` | Copy files to hosts |
| `conf_sysrc` | `sysrc` | FreeBSD rc.conf settings |
| `conf_cron` | `cron` | Cron job management |
| `conf_file` | `file` | File/directory permissions and ownership |
| `conf_get_url` | `get_url` | Download files from URLs |

### Pre-tasks and post-tasks

Run tasks before and after roles:

```yaml
---
- hosts: all
  become: true
  gather_facts: true

  pre_tasks:
    - name: Update apt cache
      ansible.builtin.apt:
        update_cache: true
        cache_valid_time: 3600
      when: ansible_os_family == "Debian"
      tags: packages

  roles:
    - role: packages
      tags: packages
    - role: users
      tags: users

  post_tasks:
    - name: Reboot if required
      ansible.builtin.reboot:
      when: reboot_required | default(false)
      tags: reboot
```

### Importing secondary playbooks

Split large playbooks into multiple files:

```yaml
---
- import_playbook: playbook-base.yml
- import_playbook: playbook-docker.yml
- import_playbook: playbook-monitoring.yml
```

## Variable Hierarchy

Ansible merges variables in a defined order. With flamelet tenants, a typical hierarchy is:

```
group_vars/all        # Defaults for every host
group_vars/<os>       # OS-specific overrides (debian, freebsd, openbsd)
group_vars/<function> # Function-specific overrides (docker, k3s, monitoring)
host_vars/<host>      # Per-host overrides
```

### Composable defaults

Define a base list in `group_vars/all` and extend it in more specific groups:

**`group_vars/all`:**

```yaml
package_install_default:
  - tree
  - curl
  - git
  - rsync
  - tmux

package_install: "{{ package_install_default }}"
```

**`group_vars/docker`:**

```yaml
package_install: "{{ package_install_default + ['docker.io', 'docker-compose'] }}"
```

**`group_vars/monitoring`:**

```yaml
package_install: "{{ package_install_default + ['prometheus-node-exporter'] }}"
```

This way, every host gets the base packages, and specific groups add their own on top.

## Tag-Based Deployment

Tags let you run only specific parts of a playbook. Pass them through flamelet with `-o`:

### Run by role

```bash
# Only run the packages role
flamelet -t myproject -l ansible -o "--tags packages"

# Run packages and users
flamelet -t myproject -l ansible -o "--tags packages,users"
```

### Run by action

If your tasks use fine-grained tags like `lineinfile`, `copy`, or `cron`:

```bash
# Only apply lineinfile and copy changes
flamelet -t myproject -l ansible -o "--tags lineinfile,copy"
```

### Limit by group

```bash
# Run on debian hosts only
flamelet -t myproject -l ansible -o "--limit debian"

# Run on freebsd hosts, excluding jails
flamelet -t myproject -l ansible -o "--limit freebsd,!jails"
```

### Limit by host

```bash
# Run on a single host
flamelet -t myproject -l ansible -o "--limit web-01.example"
```

### Combine tags and limits

```bash
# Run only the users role on debian hosts
flamelet -t myproject -l ansible -o "--tags users --limit debian"
```

## ansible.cfg Recommended Settings

Place an `ansible.cfg` in your tenant directory and point `CFG_ANSIBLE_CONFIG` to it.

```ini
[defaults]
# Use YAML callback for readable output
stdout_callback = yaml

# Use debug callback for detailed error output
# stdout_callback = debug

# Silence Python interpreter auto-detection warnings
interpreter_python = auto_silent

# Retry files clutter the directory
retry_files_enabled = False

# Increase parallelism
forks = 20

[ssh_connection]
# Forward SSH agent for git clones on remote hosts
ssh_args = -o ForwardAgent=yes -o ControlMaster=auto -o ControlPersist=60s

# Use SCP for file transfers (more compatible than SFTP)
transfer_method = scp

# Pipeline for faster execution
pipelining = True
```
