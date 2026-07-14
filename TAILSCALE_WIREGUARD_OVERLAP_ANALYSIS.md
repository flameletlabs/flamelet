# Tailscale vs WireGuard: Overlap Analysis

## Problem Summary

Both **Tailscale** and **WireGuard** operations are deployed on the same host (`controller.work`) without mutual exclusivity validation. This creates routing conflicts, service interference, and architectural confusion.

---

## Current Configuration Issues

### 1. **Double VPN on controller.work**

**File:** `/home/syseng/.config/flamelet/tenants/flamelet-home/vars/hosts/controller_work.py`

```python
# Lines 4-150: WireGuard (full mesh to core.home)
WIREGUARD = {
    "controller.work": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.5/32",
                "port": 51820,
                "routes": [
                    "192.168.80.0/24",      # ← work network (local)
                    "192.168.160.0/24",     # ← baar network
                    "192.168.150.0/24",     # ← home network
                    # ... 30+ additional routes
                ],
                "peers": [{...}]
            }
        }
    }
}

# Lines 152-159: Tailscale (ALSO trying to reach same networks)
TAILSCALE = {
    "controller.work": {
        "hostname": "k3s-connector",
        "advertise_routes": ["192.168.80.0/24"],  # ← SAME LOCAL NETWORK!
        "accept_routes": True,
    }
}
```

### 2. **Conceptual Conflict**

| Aspect | WireGuard | Tailscale |
|--------|-----------|-----------|
| **On controller.work** | Spoke to `core.home` (WireGuard hub) | Mesh node in Tailscale network |
| **Routes** | 10.50.0.0/24 + 40+ subnets via WireGuard | 192.168.80.0/24 via Tailscale |
| **Goal** | Reach infrastructure via backbone VPN | Advertise local work network to Tailscale mesh |
| **Conflict** | Both want to route the same traffic | Tailscale could intercept WireGuard traffic |

### 3. **Service Interference Scenarios**

#### Scenario A: Route Ownership
```
WireGuard (wg0): "192.168.80.0/24 → controller.work:192.168.80.1"
Tailscale:        "192.168.80.0/24 → tailscale0:100.x.x.x"
                  ↑ TWO SERVICES CLAIMING SAME SUBNET
```
**Result:** Routing table ambiguity. Which service wins? Depends on metric/priority.

#### Scenario B: Traffic Interception
```
User on tailscale network tries to reach 192.168.80.50 (work subnet):
  1. Tailscale intercepts (advertised route)
  2. Routes to controller.work via Tailscale
  3. Packet exits tailscale0 interface
  4. Could be lost or routed via WireGuard again
  
Risk: Loop, packet loss, latency spike, or unexpected routing
```

#### Scenario C: Service Restart Race
```
systemctl restart tailscaled
  → Tailscale flushes/reconfigures routes
  → WireGuard routes temporarily unavailable
  
systemctl restart wg-quick@wg0
  → WireGuard flushes/reconfigures routes  
  → Tailscale routes temporarily unavailable
  
Risk: Brief connectivity loss even though one VPN is working
```

---

## Design Analysis

### Why This Overlap Exists

1. **No Mutual Exclusivity Validation**
   - Framework allows both `WIREGUARD` and `TAILSCALE` configs on same host
   - No validation in loaders or operations to prevent this
   - No documentation warning against this pattern

2. **Different Use Cases**
   - **WireGuard** = Infrastructure backbone (permanent, enterprise mesh)
   - **Tailscale** = Additional VPN layer for specific access patterns
   - Could theoretically coexist, but:
     - Not clearly documented
     - Routing config conflicts in practice
     - No guidance on which routes go where

3. **PiKVM Exception**
   - `pikvm.baar` has **only Tailscale** (correct)
   - Advertises local subnet via Tailscale mesh
   - No WireGuard → no conflict ✓

---

## Root Causes

### 1. Missing Configuration Validation
```python
# core/tasks/loader.py or core/operations/wireguard.py + core/operations/tailscale.py
# Should validate: if both WIREGUARD and TAILSCALE on same host, check for overlap

# Current behavior: Deploy both without warning
# Expected behavior: Warn or error if:
#   - Both have overlapping routes/advertise_routes
#   - Same allowed_ips + advertise_routes
#   - Both on same interface name (unlikely but possible)
```

### 2. Incomplete Task Documentation
**CLAUDE.md** says:

```markdown
#### `wireguard` — WireGuard VPN
...
#### `tailscale` — Tailscale VPN
...
# No mention of:
# - When to use which?
# - Can they coexist?
# - Route conflict handling?
# - Service priority?
```

### 3. Route Management Inconsistency
- **WireGuard** routes via config file (static, deployed once)
- **Tailscale** routes via `--advertise-routes` flag (dynamic, can change)
- No unified route namespace validation

---

## Recommended Solutions

### Option 1: Mutual Exclusivity (Simplest)
**Approach:** Prevent both from being deployed to same host.

**Implementation:**
```python
# core/tasks/__init__.py - add validation
def _validate_task_config(config_dict):
    """Ensure no host has conflicting VPN configurations."""
    for hostname in config_dict:
        has_wg = hostname in config_dict.get("WIREGUARD", {})
        has_ts = hostname in config_dict.get("TAILSCALE", {})
        
        if has_wg and has_ts:
            raise ValueError(
                f"{hostname}: Cannot deploy both WireGuard and Tailscale. "
                f"Choose one: WireGuard for backbone, Tailscale for mesh access."
            )
```

**Pros:**
- Simple to implement
- Clear contract: one VPN per host
- Prevents routing conflicts by design

**Cons:**
- Might be too restrictive
- Prevents hybrid scenarios (if they were valid)

### Option 2: Route Conflict Detection (Better)
**Approach:** Detect and warn about overlapping routes.

**Implementation:**
```python
# core/operations/wireguard.py + core/operations/tailscale.py
def _check_route_overlap(wg_allowed_ips, ts_advertise_routes):
    """Detect overlapping routes between WireGuard and Tailscale."""
    for wg_subnet in wg_allowed_ips:
        for ts_subnet in ts_advertise_routes:
            if subnets_overlap(wg_subnet, ts_subnet):
                return True, (wg_subnet, ts_subnet)
    return False, None

# In add_wireguard_ops() and add_tailscale_ops():
#   - Load both configs
#   - Check for overlap
#   - Warn or error if found
```

**Pros:**
- Allows legitimate hybrid use (if needed)
- Catches actual conflicts only
- Can be opt-out with `--force`

**Cons:**
- More complex implementation
- Requires subnet overlap library/logic

### Option 3: Separate Networks (Recommended)
**Approach:** Document clear separation - use WireGuard for infrastructure backbone, Tailscale for supplementary access.

**Implementation:**
```python
# CLAUDE.md - Add section:
"""
### Choosing Between WireGuard and Tailscale

**Use WireGuard if:**
- Deploying infrastructure backbone (multi-site mesh)
- Need static, pre-configured routes
- Route ownership is permanent
- Requires FreeBSD/OpenBSD support

**Use Tailscale if:**
- Adding temporary mesh access
- Need dynamic route advertisement
- Want centralized management (Tailscale console)
- Only Linux/FreeBSD needed

**DO NOT use both on the same host unless:**
- WireGuard routes = backbone infrastructure (10.50.0.0/24)
- Tailscale routes = supplementary access (different subnet)
- Routes do NOT overlap

**Example (VALID):**
controller.work:
  - WireGuard: routes to all infrastructure (10.50.0.0/24, etc.)
  - Tailscale: advertises ONLY local work subnet (192.168.80.0/24)
  - Result: Two separate VPN layers, no overlap
  
**Example (INVALID - WILL CONFLICT):**
controller.work:
  - WireGuard: includes "192.168.80.0/24" in allowed_ips
  - Tailscale: advertises "192.168.80.0/24"
  - Result: CONFLICT - both claim same route
"""
```

**Pros:**
- Educates operator on design
- No code changes needed initially
- Allows flexibility when appropriate

**Cons:**
- Relies on operator understanding
- No automated enforcement

---

## Recommended Fix for controller.work

**Current (CONFLICTING):**
```python
# controller_work.py

WIREGUARD = {
    "controller.work": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.5/32",
                "peers": [{
                    "allowed_ips": [
                        "10.50.0.0/24",     # Core backbone
                        "192.168.80.0/24",  # ← CONFLICT: Also advertised via Tailscale
                        # ... other infrastructure
                    ]
                }]
            }
        }
    }
}

TAILSCALE = {
    "controller.work": {
        "advertise_routes": ["192.168.80.0/24"],  # ← DUPLICATE!
    }
}
```

**Recommended FIX (choose ONE path):**

**Path A: Use WireGuard Only (for backbone)**
```python
# Remove TAILSCALE, keep WireGuard with all routes
WIREGUARD = {
    "controller.work": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.5/32",
                "peers": [{
                    "allowed_ips": [
                        # Full infrastructure mesh
                        "10.50.0.0/24",      # Core (hub)
                        "192.168.80.0/24",   # Work (local)
                        "192.168.160.0/24",  # Baar
                        "192.168.150.0/24",  # Home
                        # etc.
                    ]
                }]
            }
        }
    }
}

# Remove TAILSCALE entirely
```

**Path B: Use Tailscale + WireGuard Differently**
```python
# WireGuard = Core backbone to central hub only
WIREGUARD = {
    "controller.work": {
        "interfaces": {
            "wg0": {
                "address": "10.50.0.5/32",
                "peers": [{
                    "allowed_ips": [
                        "10.50.0.0/24",    # Core backbone ONLY
                    ]
                }]
            }
        }
    }
}

# Tailscale = Mesh access to all nodes
TAILSCALE = {
    "controller.work": {
        "advertise_routes": ["192.168.80.0/24"],  # Work network
        "accept_routes": True,  # Accept other nodes' advertised routes
    }
}
# Result: Tailscale provides mesh connectivity, WireGuard provides hub connection
```

---

## Action Items

### Immediate
1. **Fix controller.work** - Choose Path A or B above
2. **Document decision** - Update CLAUDE.md with VPN selection criteria

### Short-term
3. **Add validation** - Detect mutual exclusivity or route overlap at deployment time
4. **Add tests** - Test both operations together, verify no conflicts

### Long-term
5. **Unified VPN framework** - Abstraction layer for multiple VPN backends
6. **Route namespace isolation** - Separate route tables by VPN type

---

## References

- WireGuard operation: `core/operations/wireguard.py`
- Tailscale operation: `core/operations/tailscale.py`
- Controller config: `~/.config/flamelet/tenants/flamelet-home/vars/hosts/controller_work.py`
- Task registry: `core/tasks/__init__.py`
- Config loaders: `core/tasks/loader.py`
