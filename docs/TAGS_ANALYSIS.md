# Flamelet v2 Framework - Major Service Tags & Components

## Discovered from Old Ansible Playbook

### PHASE 1: Foundation (Already Implemented ✅)
- **users** — User provisioning with SSH keys + passwords
- **groups** — System group creation
- **sudo** — Sudoers configuration (Linux)

### PHASE 2: System Configuration (Partially Implemented ✅)
- **packages** — OS-specific package installation (apt/pkg/pkg_add)
- **sysctl** — Kernel parameters (ip_forward, net.*, etc.)
- **sysrc** — BSD rc.conf configuration (FreeBSD/OpenBSD)
- **timezone** — System timezone
- **services** — Service management (systemd/service/rcctl)

### PHASE 3: Network & Security (Implemented ✅)
- **wireguard** — VPN (FreeBSD INI + OpenBSD ifconfig formats)
- **unbound** — DNS resolver configuration
- **pf** — Firewall rules (OpenBSD/FreeBSD only)

### PHASE 4: Monitoring & Observability (Implemented ✅)
- **monit** — Process monitoring (monitrc generation)
- **node_exporter** — Prometheus node exporter

### PHASE 5: Mail & Communication (Implemented ✅)
- **opensmtpd** — Mail relay configuration

### PHASE 6: Containers & Orchestration (Partially Implemented)
- **docker** — Docker daemon + Docker Compose (Implemented ✅)
- **k3s** — Kubernetes server/worker setup ⏳ NEEDS IMPLEMENTATION
- **registry** — Docker registry ⏳ NEEDS IMPLEMENTATION

### PHASE 7: Advanced Services (⏳ NEEDS IMPLEMENTATION)
- **virtualization** — vm-bhyve (FreeBSD hypervisor) + Bastille (jails)
- **storage** — NAS, ZFS, backup/restore
- **nginx** — Web server + reverse proxy
- **postgresql** — Database server (currently in jails)
- **grafana** — Metrics dashboard
- **prometheus** — Metrics collection (if used)

### PHASE 8: Utility Operations (Implemented ✅)
- **files** — Generic file operations
- **get_url** — Download remote files
- **lineinfile** — Line-based file editing
- **blockinfile** — Block-based file editing
- **copy** — File copying with content
- **shell** — Execute shell commands
- **raw** — Execute raw commands
- **systemd** — Systemd service management

---

## Service Tag Summary by Complexity

### Simple (< 100 lines)
- timezone
- sysrc
- node_exporter
- services

### Medium (100-200 lines)
- pf
- unbound
- monit
- opensmtpd
- wireguard

### Complex (> 200 lines)
- docker (with compose stacks + storage)
- k3s (server + worker bootstrap)
- virtualization (vm-bhyve + jails)
- storage (ZFS + backups)
- postgresql (jail setup + replication)

---

## Unbound Services (Based on Infrastructure Audit)

From 25-host inventory:

**Network Services:**
- firewalls (pf on OpenBSD/FreeBSD)
- VPN (WireGuard)
- DNS (Unbound)
- DHCP (OpenBSD controller)
- Mail relay (OpenSMTPD)

**Infrastructure Services:**
- Hypervisors (vm-bhyve on FreeBSD)
- NAS/Storage (ZFS, TrueNAS)
- Kubernetes (k3s control plane + workers)
- Docker (build host, registries)
- Monitoring (Monit, Node Exporter, Prometheus, Grafana)

**Database Services (in jails):**
- PostgreSQL (replicated across locations)

**Backup Services:**
- UrBackup
- BackupPC

---

## Tag Implementation Priority

### Tier 1 (Production Ready - 14/14)
✅ users, groups, sudo, packages, sysctl, sysrc, timezone, services, files, wireguard, unbound, pf, monit, docker, opensmtpd, node_exporter, get_url, lineinfile, blockinfile, copy, shell, raw, systemd

### Tier 2 (Required - 3/3)
⏳ k3s, virtualization, storage

### Tier 3 (Optional - 5/5)
⏳ registry (Docker), nginx, postgresql, grafana, prometheus

---

## Configuration Patterns Discovered

1. **Per-OS Configuration Files:**
   - FreeBSD: /usr/local/etc/<service>/<name>.conf
   - OpenBSD: /etc/<service>/<name>.conf
   - Linux: /etc/<service>/<name>.conf or /etc/<service>.d/

2. **Service Enable Patterns:**
   - FreeBSD: `sysrc <service>_enable=YES`
   - OpenBSD: `rcctl enable <service>`
   - Linux: `systemctl enable <service>`

3. **Configuration Inheritance (3-layer):**
   - all.py — Global defaults for all hosts
   - location/*.py — Location-specific overrides (baar, home, work, pangea)
   - hosts/*.py — Per-host custom configurations

4. **Post-deployment Hooks:**
   - Service restart on config change
   - Command execution (shell/raw)
   - File ownership/permissions
   - Validation before apply

