# Provisioning Verification Guide

How to know if provisioning operations were actually applied successfully.

## In CI (Automated)

The GitHub Actions workflow now includes three levels of verification:

### 1. Real Provisioning Tests
**Location:** `.github/workflows/ci.yml` → "Test real provisioning (apply operations)"

Runs actual provisioning (not dry-run) on `@local` host:
- `sysctl` — kernel parameters
- `monit` — process monitoring config
- `packages` — package list operation
- `services` — systemd service management

Each operation:
- Uses `set -e` to fail build on error
- Logs output to `/tmp/{task}.log`
- Checks for operation-specific keywords in logs
- Reports success/failure explicitly

### 2. Inline State Verification
**Location:** `.github/workflows/ci.yml` → "Verify provisioning effects"

Immediately after provisioning, checks system state:
- Runs `sysctl` to verify kernel parameters were set
- Checks for monit config files (`/etc/monit.conf`, `/etc/monit.d`)
- Verifies systemd service state
- Reports what actually changed

### 3. Comprehensive Verification Script
**Location:** `tests/verify_provisioning.py`

Run anytime to check provisioning results:

```bash
# Check all operations
python3 tests/verify_provisioning.py

# Check specific operations
python3 tests/verify_provisioning.py --task sysctl --task monit
```

Verifies:
- **Sysctl:** Checks if `net.ipv4.ip_forward`, `vm.swappiness` are set correctly
- **Monit:** Checks if config files exist and are readable
- **Services:** Checks if SSH service is enabled
- **Packages:** Reports operation status (packages only gather facts in test env)

## Local Testing

### Before committing, test locally:

```bash
# 1. Dry-run (plan without applying)
FLAMELET_LOCAL=1 TENANT_PATH=tenants/example \
  python3 -m core.cli --dry --task all -v

# 2. Real provisioning (apply operations)
FLAMELET_LOCAL=1 TENANT_PATH=tenants/example \
  python3 -m core.cli --task all -v

# 3. Verify results
python3 tests/verify_provisioning.py
```

## How Each Operation Reports Success

| Operation | Success Indicator | File Evidence |
|-----------|-------------------|----------------|
| **sysctl** | "✓ sysctl" in logs, kernel params readable | `/proc/sys/net/ipv4/ip_forward` |
| **monit** | "monit" keyword in logs | `/etc/monit.conf`, `/etc/monit.d/*` |
| **services** | "service" keyword in logs | `systemctl is-enabled ssh` returns 0 |
| **packages** | "package" keyword in logs | N/A in test (would check `dpkg -l` in prod) |
| **users** | "user" keyword in logs | `getent passwd username` returns user |
| **docker** | "docker" keyword in logs | `docker --version` succeeds |

## CI Success Criteria

The smoke job passes when:

1. ✅ All operations complete without error (exit code 0)
2. ✅ Operation keywords appear in logs
3. ✅ System state checks confirm changes took effect
4. ✅ Verification script runs successfully

If any step fails, the build fails explicitly (not silently).

## Understanding Output

### Real provisioning test output example:

```
[1/4] Testing sysctl provisioning...
Creating config for @local...
✓ Running operation: write sysctl config
✓ Running operation: reload sysctl
✓ sysctl operations executed
```

### Verification script output example:

```
=== Provisioning Verification Results ===

Sysctl Parameters:
  ✓ net.ipv4.ip_forward = 1
  ✓ vm.swappiness = 10

Monit Configuration:
  ✓ monit config exists
  ✓ monit.d directory exists

Services Management:
  ✓ ssh is enabled
```

## Troubleshooting

### Operations don't show in logs
- Check if operation was filtered by OS family (e.g., docker won't run on FreeBSD)
- Check if host is in config (must be in `vars/{all,location,hosts}.py`)

### Verification shows "not found" but logs show operations ran
- Some operations may be skipped in containers (e.g., system-level changes)
- Check CI log for actual operation output (may be in details, not summary)

### "Exit code X" failures
- Real provisioning tests now fail the build on any error
- Check `/tmp/{task}.log` in CI logs for full output
- Verify tenant config at `tenants/example/vars/all.py` is correct

## Adding New Operations

When adding a new operation, ensure:

1. Operation logs a clear success message
2. Verification script can check the result (update `tests/verify_provisioning.py`)
3. CI workflow includes it in real provisioning tests (`.github/workflows/ci.yml`)
4. Example tenant has test config in `tenants/example/vars/all.py`

Then CI will automatically verify your new operation works.
