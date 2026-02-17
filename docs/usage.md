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

A powerful pattern in flamelet tenants is to define configuration changes as data in variables, then apply them with generic tasks in the playbook. This keeps playbooks reusable and moves all host/group specifics into `group_vars` and `host_vars`.

The available `conf_*` types and their corresponding Ansible modules:

| Variable | Ansible module | Use case |
| :------- | :------------- | :------- |
| `conf_lineinfile` | `lineinfile` | Single-line edits in config files |
| `conf_blockinfile` | `blockinfile` | Multi-line block insertions |
| `conf_copy` | `copy` | Deploy file content to hosts |
| `conf_file` | `file` | File/directory permissions, ownership, symlinks |
| `conf_get_url` | `get_url` | Download files from URLs |
| `conf_sysrc` | `sysrc` | FreeBSD rc.conf settings |
| `conf_cron` | `cron` | Cron job management |
| `conf_shell` | `shell` | Shell commands to execute |

### The _default + _custom composition pattern

Each `conf_*` variable is composed from two lists that are merged at runtime:

- **`conf_*_default`** — Shared baseline defined in `group_vars/all`. Applied to every host.
- **`conf_*_custom`** — Additions defined in `group_vars/<os>`, `group_vars/<function>`, or `host_vars/<host>`. Applied only where defined.

The final `conf_*` variable is the concatenation of both:

```yaml
conf_copy: "{{ conf_copy_default|default([]) + conf_copy_custom|default([]) }}"
```

This means you never lose the shared defaults when adding host-specific configurations — they are additive.

**Flow:**

```
conf_*_default (group_vars/all)     +     conf_*_custom (group_vars/<os>, host_vars/<host>)
            └──────────────────── merged into ────────────────────┘
                                  conf_*
                            (used in playbook loops)
```

#### Step 1: Define defaults in group_vars/all

These apply to every host in the inventory:

```yaml
# group_vars/all

conf_lineinfile_default:
  - service: sshd
    regexp: "^PermitRootLogin"
    line: "PermitRootLogin prohibit-password"
    path: /etc/ssh/sshd_config
  - service: sshd
    regexp: "^PasswordAuthentication"
    line: "PasswordAuthentication no"
    path: /etc/ssh/sshd_config

conf_copy_default:
  - service: ''
    content: |
      # Managed by flamelet
      nameserver 1.1.1.1
      nameserver 9.9.9.9
    dest: /etc/resolv.conf
    group: "{{ os_default_group[ansible_os_family] }}"
    mode: '0644'

conf_get_url_default:
  - url: 'https://example.com/scripts/health-check.sh'
    dest: '/usr/local/bin/health-check.sh'
    owner: 'root'
    group: "{{ os_default_group[ansible_os_family] }}"
    mode: '0755'
```

#### Step 2: Initialize custom as empty in group_vars

Set `_custom` to an empty list in OS-level group_vars so the merge always works, even for hosts that don't define their own custom list:

```yaml
# group_vars/freebsd

conf_lineinfile_custom: []
conf_blockinfile_custom: []
conf_copy_custom: []
conf_file_custom: []
conf_get_url_custom: []
conf_shell_custom: []
conf_sysrc_custom: []

# Compose the final variables
conf_lineinfile: "{{ conf_lineinfile_default|default([]) + conf_lineinfile_custom|default([]) }}"
conf_blockinfile: "{{ conf_blockinfile_default|default([]) + conf_blockinfile_custom|default([]) }}"
conf_copy: "{{ conf_copy_default|default([]) + conf_copy_custom|default([]) }}"
conf_file: "{{ conf_file_default|default([]) + conf_file_custom|default([]) }}"
conf_get_url: "{{ conf_get_url_default|default([]) + conf_get_url_custom|default([]) }}"
conf_shell: "{{ conf_shell_default|default([]) + conf_shell_custom|default([]) }}"
conf_sysrc: "{{ conf_sysrc_default|default([]) + conf_sysrc_custom|default([]) }}"
```

#### Step 3: Add host-specific customizations in host_vars

Override `_custom` in a host's vars file to add host-specific configurations on top of the defaults:

```yaml
# host_vars/db-01.example

conf_lineinfile_custom:
  - service: bsnmpd
    regexp: 'location := .*'
    line: 'location := "Datacenter A, Rack 4"'
    state: present
    path: /etc/snmpd.config
  - service: bsnmpd
    regexp: 'contact := .*'
    line: 'contact := "ops@example.com"'
    state: present
    path: /etc/snmpd.config
conf_lineinfile: "{{ conf_lineinfile_default|default([]) + conf_lineinfile_custom|default([]) }}"

conf_copy_custom:
  - service: ''
    content: |
      10.0.0.5    db-01 db-01.example
      10.0.0.6    db-02 db-02.example
    group: wheel
    mode: '0644'
    dest: /etc/hosts
  - service: devfs
    content: |
      [localrules=10]
      add path fuse mode 0666
    group: wheel
    mode: '0644'
    dest: /etc/devfs.rules
conf_copy: "{{ conf_copy_default|default([]) + conf_copy_custom|default([]) }}"

conf_sysrc_custom:
  - name: zfs_enable
    value: "YES"
    state: present
    path: /etc/rc.conf
  - name: devfs_system_ruleset
    value: "localrules"
    state: present
    path: /etc/rc.conf
conf_sysrc: "{{ conf_sysrc_default|default([]) + conf_sysrc_custom|default([]) }}"
```

When the playbook runs on `db-01.example`, it gets both the shared SSH hardening from defaults and the host-specific SNMP, hosts file, and sysrc entries from custom.

#### Step 4: Playbook tasks loop over the merged variable

The playbook only references the final `conf_*` variable — it doesn't need to know about the default/custom split:

```yaml
- name: lineinfile
  ansible.builtin.lineinfile:
    regexp: '{{ item.regexp }}'
    line: '{{ item.line }}'
    path: '{{ item.path }}'
    state: '{{ item.state | default("present") }}'
  loop: '{{ conf_lineinfile | default([]) }}'
  register: conf_lineinfile_changed
  tags: [ 'post', 'lineinfile' ]

- name: copy
  ansible.builtin.copy:
    content: '{{ item.content }}'
    dest: '{{ item.dest }}'
    group: '{{ item.group }}'
    mode: '{{ item.mode }}'
  loop: '{{ conf_copy | default([]) }}'
  register: conf_copy_changed
  tags: [ 'post', 'copy' ]

- name: blockinfile
  ansible.builtin.blockinfile:
    block: '{{ item.block }}'
    path: '{{ item.path }}'
  loop: '{{ conf_blockinfile | default([]) }}'
  register: conf_blockinfile_changed
  tags: [ 'post', 'blockinfile' ]

- name: file
  ansible.builtin.file:
    dest: '{{ item.dest }}'
    state: '{{ item.state }}'
    owner: '{{ item.owner | default("root") }}'
    group: '{{ item.group | default("wheel") }}'
    mode: '{{ item.mode | default("0755") }}'
  loop: '{{ conf_file | default([]) }}'
  tags: [ 'post', 'file' ]

- name: get_url
  ansible.builtin.get_url:
    url: '{{ item.url }}'
    dest: '{{ item.dest }}'
    owner: '{{ item.owner | default("root") }}'
    group: '{{ item.group }}'
    mode: '{{ item.mode }}'
  loop: '{{ conf_get_url | default([]) }}'
  tags: [ 'post', 'get_url' ]

- name: sysrc
  community.general.sysrc:
    name: '{{ item.name }}'
    value: '{{ item.value }}'
    state: '{{ item.state }}'
    path: '{{ item.path | default("/etc/rc.conf") }}'
  loop: '{{ conf_sysrc | default([]) }}'
  when: ansible_os_family == "FreeBSD"
  tags: [ 'post', 'sysrc' ]
```

### Automatic service restart on config change

Each `conf_*` item can include a `service` field. When the task registers a change, the playbook collects affected services and restarts them automatically:

```yaml
- name: Collect services to restart (copy)
  set_fact:
    services_to_restart_copy: "{{ services_to_restart_copy | default([]) + [item.service] }}"
  loop: "{{ conf_copy }}"
  when: conf_copy_changed.changed and item.service is defined and item.service != ""

- name: Restart services (copy)
  ansible.builtin.service:
    name: "{{ item }}"
    state: restarted
  loop: "{{ services_to_restart_copy | unique }}"
  when: conf_copy_changed.changed | bool
```

Items can also include a `command` field for post-change commands instead of (or in addition to) service restarts:

```yaml
- name: Collect commands to exec (copy)
  set_fact:
    commands_to_exec_copy: "{{ commands_to_exec_copy | default([]) + [item.command] }}"
  loop: "{{ conf_copy }}"
  when: conf_copy_changed.changed and item.command is defined and item.command != ""
```

### Item structure reference

Each `conf_*` type has a specific item structure:

**conf_copy:**

```yaml
- service: 'nginx'              # Service to restart on change (empty string = none)
  command: '/usr/local/bin/reload-app'  # Command to run on change (optional)
  content: |                    # Inline file content
    server_name example.com;
  dest: '/etc/nginx/conf.d/app.conf'
  group: 'wheel'
  mode: '0644'
  owner: 'root'                 # Optional, defaults to root
  validate: 'nginx -t -c %s'   # Optional validation command
```

**conf_lineinfile:**

```yaml
- service: 'sshd'
  regexp: '^PermitRootLogin'
  line: 'PermitRootLogin prohibit-password'
  state: 'present'              # present or absent
  path: '/etc/ssh/sshd_config'
  insertbefore: '#LoginGraceTime'  # Optional insertion point
  validate: '/usr/sbin/sshd -t -f %s'
```

**conf_blockinfile:**

```yaml
- service: 'pf'
  command: 'pfctl -f /etc/pf.conf'
  block: |
    pass in on egress proto tcp to port { 80, 443 }
    pass out all
  path: '/etc/pf.conf'
  state: 'present'
```

**conf_file:**

```yaml
- dest: '/var/data/backups'
  state: 'directory'            # file, directory, link, absent
  recurse: true
  owner: 'backup'
  group: 'wheel'
  mode: '0750'
```

**conf_get_url:**

```yaml
- url: 'https://example.com/scripts/monitor.sh'
  dest: '/usr/local/bin/monitor.sh'
  owner: 'root'
  group: 'wheel'
  mode: '0755'
```

**conf_sysrc (FreeBSD):**

```yaml
- name: 'nginx_enable'
  value: 'YES'
  state: 'present'
  path: '/etc/rc.conf'
```

**conf_shell:**

```yaml
- cmd: 'zpool scrub tank'
  creates: '/var/log/scrub.done'  # Optional, skip if file exists
```

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
