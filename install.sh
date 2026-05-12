#!/usr/bin/env bash
# Flamelet v2 installer — installs Python/pyinfra-based infrastructure automation

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# XDG Base Directory Specification
FRAMEWORK_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/flamelet"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/flamelet"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/flamelet"
REPO_URL="${FLAMELET_REPO:-https://github.com/flameletlabs/flamelet.git}"
BRANCH="${FLAMELET_BRANCH:-main}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check dependencies
check_dependencies() {
    local missing=()

    for cmd in git python3 pip; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        echo "Install with:"
        echo "  Ubuntu/Debian: apt-get install git python3-pip"
        echo "  macOS: brew install git python3"
        echo "  Arch: pacman -S git python"
        exit 1
    fi
}

# Clone or update framework
setup_framework() {
    if [ -d "$FRAMEWORK_DIR/.git" ]; then
        log_info "Updating framelet in $FRAMEWORK_DIR"
        git -C "$FRAMEWORK_DIR" fetch origin "$BRANCH"
        git -C "$FRAMEWORK_DIR" checkout "$BRANCH"
        git -C "$FRAMEWORK_DIR" pull --ff-only
    else
        log_info "Installing flamelet to $FRAMEWORK_DIR"
        mkdir -p "$(dirname "$FRAMEWORK_DIR")"
        git clone --branch "$BRANCH" "$REPO_URL" "$FRAMEWORK_DIR"
    fi
}

# Create scaffold config
setup_config() {
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$CACHE_DIR"

    if [ ! -f "$CONFIG_DIR/config.toml" ]; then
        log_info "Creating config scaffold at $CONFIG_DIR/config.toml"
        cat > "$CONFIG_DIR/config.toml" <<'EOF'
[framework]
version = "2.0.0"

[tenants]
# Register your tenants here
# Format: tenant_name = "path/to/tenant/directory"
# Example: home = "~/src/my-infrastructure/tenants/home"
EOF
    else
        log_warn "Config already exists at $CONFIG_DIR/config.toml"
    fi
}

# Install Python dependencies
setup_python() {
    log_info "Installing Python dependencies"

    if ! command -v pipx &> /dev/null; then
        log_info "Installing pipx"
        pip3 install --user pipx
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if ! pipx list 2>/dev/null | grep -q pyinfra; then
        log_info "Installing pyinfra via pipx"
        pipx install pyinfra
    fi

    log_info "Injecting test dependencies"
    pipx inject pyinfra pytest ruff 2>/dev/null || true
}

# Main
main() {
    echo "======================================"
    echo "     Flamelet v2 Installer"
    echo "     Python/pyinfra Infrastructure"
    echo "======================================"
    echo ""

    check_dependencies
    setup_framework
    setup_config
    setup_python

    echo ""
    log_info "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit your tenants in: $CONFIG_DIR/config.toml"
    echo "  2. Clone or create a tenant repository"
    echo "  3. Run: source $FRAMEWORK_DIR/tenants/<name>/run.py --help"
    echo ""
    echo "Framework location: $FRAMEWORK_DIR"
    echo "Config location:    $CONFIG_DIR"
    echo ""
    echo "Documentation: $FRAMEWORK_DIR/README.md"
}

main "$@"
