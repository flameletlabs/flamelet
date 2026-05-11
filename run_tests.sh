#!/bin/bash
# Comprehensive test runner for Flamelet v2 framework

set -e

FRAMEWORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-/home/syseng/.local/share/pipx/venvs/pyinfra/bin/python3}"
PYTEST="${PYTEST:-$PYTHON -m pytest}"

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║         FLAMELET v2 COMPREHENSIVE TEST SUITE                          ║"
echo "║                    All 23 Operations & Loaders                        ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

cd "$FRAMEWORK_ROOT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

# Function to run a test category
run_test_category() {
    local category="$1"
    local pattern="$2"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $category"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if $PYTEST tests/ -k "$pattern" -v 2>&1 | tee /tmp/test_output.txt; then
        echo -e "${GREEN}✓ $category passed${NC}"
        ((pass_count++))
    else
        echo -e "${RED}✗ $category failed${NC}"
        ((fail_count++))
    fi
    ((test_count++))
}

# Run test categories

echo "[1] OPERATIONS IMPORT TESTS"
echo "Verifying all 23 operation modules import correctly..."
run_test_category "Phase 1 Operations (users, groups, sudo, packages, services)" "TestPhase1Operations"

run_test_category "Phase 2 Operations (sysctl, files)" "TestPhase2Operations"

run_test_category "Phase 3a Operations (wireguard, unbound, pf, monit, opensmtpd, docker, node_exporter)" "TestPhase3aOperations"

run_test_category "Tier 2 Required Operations (k3s, virtualization, storage)" "TestPhase3bTier2Operations"

run_test_category "Optional Enhanced Operations (nginx, postgresql, prometheus, registry)" "TestPhase3bOptionalOperations"

run_test_category "All Operations Existence Check" "TestAllOperationsExist"

echo ""
echo "[2] PYINFRA INTEGRATION TESTS"
echo "Verifying PyInfra built-in operations are available..."
run_test_category "PyInfra Integration" "TestPyInfraIntegration"

echo ""
echo "[3] TENANT CONFIGURATION TESTS"
echo "Verifying tenant vars loaders and configuration..."
run_test_category "Tenant Vars Loaders" "TestTenantVarsLoaders"

run_test_category "Config Loader Functionality" "TestConfigLoaderFunctionality"

run_test_category "Inventory Integration" "TestInventoryIntegration"

run_test_category "Tenant run.py Integration" "TestTenantRunPy"

run_test_category "Operation Compatibility" "TestOperationCompatibility"

echo ""
echo "[4] CONFIGURATION GENERATION TESTS"
echo "Verifying config generation functions..."
run_test_category "Nginx Config Generation" "TestNginxConfigGeneration"

run_test_category "Prometheus Config Generation" "TestPrometheusConfigGeneration"

run_test_category "Registry Config Generation" "TestRegistryConfigGeneration"

run_test_category "Unbound Config Generation" "TestUnboundConfigGeneration"

run_test_category "WireGuard Config Generation" "TestWireGuardConfigGeneration"

run_test_category "pf Firewall Config Generation" "TestPFConfigGeneration"

run_test_category "Monit Config Generation" "TestMonitConfigGeneration"

run_test_category "OpenSMTPD Config Generation" "TestOpenSMTPDConfigGeneration"

run_test_category "PostgreSQL Config" "TestPostgreSQLConfigGeneration"

run_test_category "Docker Config Generation" "TestDockerConfigGeneration"

run_test_category "Config Validation" "TestConfigValidation"

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                        TEST SUMMARY                                   ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Test Categories:  $test_count"
echo -e "Passed:  ${GREEN}$pass_count${NC}"
echo -e "Failed:  ${RED}$fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "Framework Status:"
    echo "  ✓ 23 operations implemented and importable"
    echo "  ✓ All configuration loaders working"
    echo "  ✓ Tenant integration verified"
    echo "  ✓ Config generation functions validated"
    echo "  ✓ PyInfra integration confirmed"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please review the output above for details."
    exit 1
fi
