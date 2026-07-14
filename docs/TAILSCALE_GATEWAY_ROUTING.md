# Tailscale Gateway Routing Implementation

## Overview

Gateway routing enables clients on a local network to transparently reach remote subnets via a Tailscale-connected hypervisor acting as a gateway. This document covers implementation on FreeBSD (using pf) and Linux (using netfilter/nftables).

## Architecture

```
Home Network                    Tailscale Mesh                 Baar Network
192.168.150.0/24                 (P2P VPN)                   192.168.160.0/24

[iPhone]                                                     [virt-01-baar]
192.168.150.x                                               192.168.160.1
    |                                                             |
    | (1) ARP for gateway                                        |
    | (2) IP packet SRC=192.168.150.x, DST=192.168.160.1        |
    v                                                             |
[virt.home Gateway]            [Tailscale Peer]               (Active)
192.168.150.2                   100.89.149.47
Tailscale: 100.89.149.47        (virt-01-baar endpoint)
    |
    | (3) pf NAT: SRC → 100.89.149.47
    | (4) Route to tailscale0
    v
[Tailscale Interface]
tailscale0
    |
    | (5) P2P encrypted tunnel
    v
[Remote Tailscale Endpoint]
    |
    | (6) Route to 192.168.160.0/24
    v
[Remote Hypervisor Gateway]
virt-01-baar
    |
    | (7) Process and reply
    v
[Response packet back to virt.home]
SRC=192.168.160.1, DST=100.89.149.47
    |
    | (8) pf reverse-NAT: DST → 192.168.150.x
    v
[iPhone receives response]
```

## FreeBSD Implementation (pf)

### Key Concepts

**pf (packet filter):**
- Stateful firewall built into FreeBSD/OpenBSD kernel
- Rules file: `/etc/pf.conf`
- Processing pipeline: Macros → Tables → Options → Normalization → Translation → Filtering

**NAT (Network Address Translation):**
- Translation phase rule: `nat on interface ... -> (interface)`
- Dynamic interface references: `($interface)` expands to interface's IP at runtime
- Bidirectional: forward traffic gets translated, return traffic auto-reverse-translated via state tracking

**Configuration Structure:**

```freebsd
# Options: define macros and skip behavior
ext_if = "em0"
vpn_if = "tailscale0"
bridge_if = "bridge10"
set skip on lo                          # Don't skip VPN interfaces!
set require-order no                    # Allow flexible rule ordering

# Translation: NAT rules for gateway routing
nat on $vpn_if inet from 192.168.150.0/24 to 192.168.160.0/24 -> ($vpn_if)
nat on $bridge_if inet from 192.168.160.0/24 to 192.168.150.0/24 -> ($bridge_if)

# Filtering: pass rules for bidirectional traffic
pass in on $bridge_if inet proto {tcp, udp} from 192.168.150.0/24 to any keep state
pass out on $vpn_if inet proto {tcp, udp} from 192.168.150.0/24 to 192.168.160.0/24 keep state
pass in on $vpn_if inet proto {tcp, udp} from 192.168.160.0/24 to any keep state
pass out on $bridge_if inet proto {tcp, udp} from 192.168.160.0/24 to 192.168.150.0/24 keep state

# Anchors: for dynamic rule injection
anchor "tailscale"
nat-anchor "tailscale"
```

### Critical Gotchas

1. **Skip Rules Break NAT**
   - ❌ `set skip on { lo tailscale0 wg1 }` prevents NAT from being applied
   - ✅ `set skip on lo` only
   - Why: NAT rules in translation phase won't match if pf skips processing

2. **Rule Ordering**
   - ❌ Don't mix translation rules with filtering rules
   - ✅ All NAT before all pass/block rules
   - Why: pf enforces section ordering (options → normalization → translation → filtering)

3. **Dynamic Interface References**
   - ❌ `nat on tailscale0 ... -> 100.89.149.47` (hardcoded IP)
   - ✅ `nat on tailscale0 ... -> ($tailscale0)` (dynamic reference)
   - Why: If Tailscale IP changes, rules auto-adapt

4. **Stateful Filtering**
   - ✅ `pass ... keep state` creates bidirectional state entries
   - Why: Return traffic automatically allowed and reverse-NATed
   - Monitor: `pfctl -s info` shows active state connections

### Deployment via Flamelet

In `vars/hosts/virt_home.py`:

```python
PF_GATEWAY_ROUTING = {
    "virt.home": {
        "role": "gateway",
        "local_subnet": "192.168.150.0/24",
        "local_ip": "192.168.150.2",
        "vpn_interface": "tailscale0",
        "remote_subnets": [
            "192.168.160.0/24",  # baar
            "192.168.180.0/24",  # pangea
            "192.168.80.0/24",   # work
        ],
        "backup_vpn": "wg0",
        "external_interface": "em0",
        "internal_bridge": "bridge10",
    }
}
```

In `core/tasks/__init__.py`:

```python
from core.operations.pf_gateway_routing import add_pf_gateway_routing_ops

TASK_REGISTRY = {
    "pf_gateway_routing": {
        "handler": add_pf_gateway_routing_ops,
        "config_attr": "PF_GATEWAY_ROUTING",
    },
}
```

Deploy:
```bash
flamelet --tenant flamelet-home --task pf_gateway_routing --limit virt.home,virt.pangea,virt-01.baar
```

## Linux Implementation (netfilter)

### Key Concepts

**netfilter/iptables:**
- Kernel packet filtering framework
- Rules chains: PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING
- Two versions: iptables (legacy) and nftables (modern)
- Configuration: runtime rules or persistent via UFW/firewalld

**MASQUERADE (Linux NAT):**
- iptables: `iptables -t nat -A POSTROUTING -o tailscale0 -j MASQUERADE`
- nftables: `table ip nat { chain postrouting { ... masquerade } }`
- Difference from pf: Dynamic by design (doesn't need interface references)

**Configuration Structure (iptables):**

```bash
#!/bin/bash
# Linux gateway routing with iptables

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Create filter chains for gateway routing
iptables -N TAILSCALE_FWD 2>/dev/null || true

# NAT: MASQUERADE traffic going to VPN interface
iptables -t nat -A POSTROUTING -o tailscale0 -j MASQUERADE

# FORWARD chain: allow bidirectional traffic
# From local clients to remote subnets
iptables -A FORWARD -i bridge0 -o tailscale0 \
  -d 192.168.160.0/24 -j ACCEPT
iptables -A FORWARD -i bridge0 -o tailscale0 \
  -d 192.168.180.0/24 -j ACCEPT

# Return traffic from remote subnets to local clients
iptables -A FORWARD -i tailscale0 \
  -s 192.168.160.0/24 -o bridge0 -j ACCEPT
iptables -A FORWARD -i tailscale0 \
  -s 192.168.180.0/24 -o bridge0 -j ACCEPT

# Allow stateful connections
iptables -A FORWARD -m state \
  --state ESTABLISHED,RELATED -j ACCEPT
```

**Configuration Structure (nftables - RECOMMENDED):**

```nftables
#!/usr/bin/nft -f

flush ruleset

table ip filter {
    chain forward {
        type filter hook forward priority 0; policy drop;

        # Stateful: allow established connections
        ct state established,related accept

        # Gateway routing: local to remote subnets
        iif bridge0 oif tailscale0 \
          ip daddr { 192.168.160.0/24, 192.168.180.0/24 } \
          accept

        # Gateway routing: remote to local
        iif tailscale0 oif bridge0 \
          ip saddr { 192.168.160.0/24, 192.168.180.0/24 } \
          accept
    }
}

table ip nat {
    chain postrouting {
        type nat hook postrouting priority 100; policy accept;

        # MASQUERADE: dynamically NAT to tailscale0's IP
        oif tailscale0 masquerade
    }
}
```

### Linux-specific Configuration

**Deployment File (ansible/roles/tailscale_gateway/templates/nftables.j2):**

```jinja2
#!/usr/bin/nft -f
# Tailscale Gateway Routing for Linux
# Host: {{ inventory_hostname }}

flush ruleset

define LOCAL_SUBNET = { {{ local_subnet }} }
define REMOTE_SUBNETS = { {{ remote_subnets | join(', ') }} }

table ip filter {
    chain forward {
        type filter hook forward priority 0; policy drop;
        ct state established,related accept

        # VPN gateway routing
        iif {{ internal_interface }} oif {{ vpn_interface }} \
          ip daddr $REMOTE_SUBNETS accept

        iif {{ vpn_interface }} oif {{ internal_interface }} \
          ip saddr $REMOTE_SUBNETS accept
    }
}

table ip nat {
    chain postrouting {
        type nat hook postrouting priority 100; policy accept;
        oif {{ vpn_interface }} masquerade
    }
}
```

## Comparison: FreeBSD pf vs Linux netfilter

| Aspect | FreeBSD pf | Linux iptables | Linux nftables |
|--------|-----------|-----------------|-----------------|
| **Config File** | `/etc/pf.conf` (unified) | Multiple runs or script | Unified `/etc/nftables.conf` |
| **Rule Order** | Enforced (options → filtering) | Chain-based, more flexible | Table-based, flexible |
| **NAT Syntax** | `nat on $if ... -> ($if)` | `iptables -t nat -A POSTROUTING` | `masquerade` in postrouting |
| **Stateful** | Automatic (keep state) | Explicit (`-m state`) | Automatic (ct state) |
| **Dynamic IPs** | `($interface)` syntax | Built-in masquerade | Built-in masquerade |
| **Persistence** | `/etc/rc.conf` (sysrc) | UFW, firewalld, or iptables-save | systemd-nftables.service |
| **Performance** | Excellent (kernel integrated) | Good (userspace control) | Excellent (kernel native) |
| **Learning Curve** | Medium (unified syntax) | Low (simple chains) | Medium (table/chain concepts) |

## Testing & Verification

### FreeBSD (pf)

```bash
# Check rules loaded
pfctl -sr              # Filter rules
pfctl -sn              # NAT rules
pfctl -s info          # State table statistics

# Test from client
ping 192.168.160.1     # Should work with 80-120ms latency via Tailscale

# Trace traffic flow
tcpdump -i bridge10 'dst net 192.168.160.0 mask 255.255.255.0'
tcpdump -i tailscale0 'dst net 192.168.160.0 mask 255.255.255.0'

# Verify NAT is applied
# tcpdump output on tailscale0 should show SRC=100.89.149.47 (virt.home's Tailscale IP)
# Not original client IP
```

### Linux (nftables)

```bash
# Check rules loaded
nft list ruleset

# Test from client
ping 192.168.160.1     # Should work

# Trace traffic
tcpdump -i tailscale0 'dst 192.168.160.1'
# Should see MASQUERADE applied

# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward  # Must be 1
```

## Troubleshooting

### Issue: Client Can Reach Gateway But Not Remote Subnets

**FreeBSD pf:**
```bash
# Check if rules are being skipped
pfctl -sr | grep 'skip'  # Should see: "set skip on lo" only

# Verify NAT rules exist
pfctl -sn | grep tailscale0

# Check state table
pfctl -s all | grep 192.168.160.1
```

**Linux:**
```bash
# Check IP forwarding enabled
sysctl net.ipv4.ip_forward     # Must be 1

# Check nftables rules
nft list ruleset

# Verify MASQUERADE
nft list table ip nat
```

### Issue: Return Traffic Doesn't Reach Client

**Cause:** Reverse-NAT not configured or filtered

**FreeBSD pf:**
```bash
# Must have reverse NAT rule:
# nat on bridge10 inet from 192.168.160.0/24 to 192.168.150.0/24 -> (bridge10)

# And passing rules for return traffic:
# pass in on tailscale0 ... from 192.168.160.0/24
# pass out on bridge10 ... to 192.168.150.0/24
```

**Linux:**
```bash
# Must have rules in both directions:
nft rule ip filter forward handle <n> list  # Check both directions exist
```

## Rollout Timeline

### Phase 1: FreeBSD Hypervisors (Week 1)
- Deploy to virt.home (primary gateway)
- Test with iPhone and dev.home VM
- Verify all 3 remote subnets reachable

### Phase 2: Other FreeBSD Hypervisors (Week 2)
- Deploy to virt.pangea
- Deploy to virt-01.baar (baar clients → home/pangea)
- Test cross-location routing

### Phase 3: Linux Servers (Week 3-4)
- Deploy to k3s-connector (work-to-home gateway routing)
- Deploy to Linux-based edge nodes if any
- Document Linux-specific procedures

### Phase 4: Maintenance & Monitoring (Ongoing)
- Add Monit checks for pf state table health
- Document emergency procedures
- Create runbooks for common issues

## References

- [FreeBSD pf documentation](https://www.freebsd.org/cgi/man.cgi?pf.4)
- [OpenBSD pf guide](https://www.openbsd.org/faq/pf/)
- [Linux netfilter/iptables](https://netfilter.org/projects/iptables/)
- [nftables wiki](https://wiki.nftables.org/)
- [Tailscale Subnet Routing](https://tailscale.com/docs/features/subnet-routes)
