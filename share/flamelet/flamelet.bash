# Flamelet functions

sshqfunc() { echo "bash -c $(printf "%q" "$(declare -f "$@"); $1 \"\$@\"")"; };

_cleanOptions_() {

    declare -a _options=("$@")
    declare -a _cleanedOptions
    local _option
    local _preserve_next=false

    for _option in "${_options[@]}"; do
        if [[ $_preserve_next == true ]]; then
            _cleanedOptions+=("\"$_option\"")
            _preserve_next=false
        elif [[ $_option == "-o" || $_option == "--option" ]]; then
            _preserve_next=true
            _cleanedOptions+=("$_option")
        elif [[ $_option == "-r" || $_option == "--remote" ]]; then
            # Skip the -r or --remote option
            continue
        else
            _cleanedOptions+=("${_option}")
        fi
    done

    printf '%s\n' "${_cleanedOptions[@]}"
}

_installRemote_() {
    local _path _files _scp_options

    _path=".flamelet/bin"
    _files="alerts.bash,arrays.bash,checks.bash,debug.bash,files.bash,setv.bash,flamelet.bash,misc.bash,template_utils.bash"

    _execute_ -vs "ssh ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }-T ${CFG_SSH_CONTROLLER}" "Cleanup" <<-EOF
    mkdir -p ${_path}/share/flamelet
    mkdir -p \${HOME}/.flamelet
    rm -f ${_path}/share/flamelet/*.bash
    rm -f ${_path}/flamelet
EOF

    # This will be preserved ${HOME}/.flamelet/env.sh

_scp_options=${CFG_SCP_OPTIONS:-${CFG_SSH_OPTIONS}}

    _execute_ -vs "scp -q -B -C ${_scp_options:+"$_scp_options" }\
$(_findBaseDir_)/../../flamelet ${CFG_SSH_CONTROLLER}:\${_path}/flamelet" \
"Install flamelet script"

    _execute_ -vs "scp -q -B -C ${_scp_options:+"$_scp_options" }\
$(_findBaseDir_)/../../VERSION ${CFG_SSH_CONTROLLER}:\${_path}/VERSION" \
"Install VERSION file"

    _execute_ -vs "scp -q -B -C ${_scp_options:+"$_scp_options" }\
$(_findBaseDir_)/{${_files}} ${CFG_SSH_CONTROLLER}:\${_path}/share/flamelet/" \
"Install flamelet libraries"

#     (_isFile_ "${HOME}/.flamelet/tenant/flamelet-${_tenant}/env.sh") && \
#         _execute_ -vs "scp -q -B -C ${_scp_options:+"$_scp_options" }\
# ${HOME}/.flamelet/tenant/flamelet-${_tenant}/env.sh ${CFG_SSH_CONTROLLER}:\${_path}/../env.sh" \
# "Install environment" || \
# info "Environment not defined"
}

_installDeps_() {

    local _cmd=()

    case $(_detectOS_) in
        linux)
            case $(_detectLinuxDistroFamily_) in
                debian)
                    _cmd=( env DEBIAN_FRONTEND=noninteractive apt-get -y install bash tree rsync git tmux ccze ncdu virt-what python3 python3-venv sshpass nmap xsltproc )
                    debug "we're on Debian family"
                    ;;
                redhat)
                    _cmd=( yum -y install bash hostname tree rsync git tmux ccze ncdu python3 )
                    debug "we're on RedHat family"
                    ;;
                *)
                    echo "we're on unknown"
                    return 1
                    ;;
            esac
            ;;
        mac)
            _os="mac"
            echo "we're on mac"
            ;;
        windows)
            _os="windows"
            echo "we're on windows"
            ;;
        freebsd)
            _cmd=( pkg install -y bash tree rsync git-lite tmux ccze ncdu wget rust nmap libxslt )
            ;;
        openbsd)
            _cmd=( pkg_add -U -I bash tree rsync-- git ncdu python3 wget rust nmap libxslt )
            ;;
        *)
            echo "we're on unknown"
            return 1
            ;;
    esac

    _runAsRoot_ "${_cmd[@]}"
}

_getSystemInfo_() {
    # DESC:
    #         TODO
    # ARGS:
    #         $1 (Optional) - String for customized message

    info "$(_detectOS_)"
    info "$(_detectLinuxDistro_)"

    success "bash ${BASH_VERSION}"

    (_commandExists_ python3 && _execute_ -vs "python3 -V" "python3 check") || warning "python3 check"
    (_commandExists_ rsync && _execute_ -s "rsync --version" "rsync check") || warning "rsync check"
    (_commandExists_ git && success "git check" ) || warning "git check"
    (_commandExists_ tmux && success "tmux check" ) || warning "tmux check"
    (_commandExists_ tree && success "tree check" ) || warning "tree check"
    (_commandExists_ ccze && success "ccze check" ) || warning "ccze check"
    (_commandExists_ ncdu && success "ncdu check" ) || warning "ncdu check"

    # case $(_detectOS_) in
    #     linux)
    #         _os="linux"
    #         ;;
    #     mac)
    #         _os="mac"
    #         ;;
    #     windows)
    #         _os="windows"
    #         ;;
    #     freebsd)
    #         _os="freebsd"
    #         ;;
    #     openbsd)
    #         _os="openbsd"
    #         ;;
    #     *)
    #         echo "we're on unknown"
    #         return 1
    #         ;;
    # esac

    ( _rootAvailable_ && success "sudo privilege escalation" ) || warning "no sudo privilege escalation"
    ( _rootAvailable_ "nosudo" && info "we are root" ) || info "we are not root"
}

_runRemote_() {
    [[ $# -lt 1 ]] && fatal "Missing required argument to ${FUNCNAME[0]}"

    local _remoteOptions="${1}"

    local _path="\${HOME}/.flamelet/bin"

    # Error handling
    declare -f _execute_ &>/dev/null || fatal "_runRemote_ needs function _execute_"

    _remoteOptions="${1//\"/\\\"}"
    debug "remote options: ${_remoteOptions}"

    _execute_ -vs "ssh ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }-q -t ${CFG_SSH_CONTROLLER} \
\"bash -c '\${_path}/flamelet ${_remoteOptions}'\"" \
"Running '\${_path}/flamelet ${_remoteOptions}' via ssh on '${CFG_SSH_CONTROLLER}'"
}

_dockerPermsAvailable_() {
    # DESC:
    #         Validate docker is available
    # OUTS:
    #         0 if true
    #         1 if false

    local _docker=false

    # if [[ ${EUID} -eq 0 ]]; then
    #     _superuser=true
    # elif [[ -z ${1:-} ]]; then
    #     debug 'Sudo: Updating cached credentials ...'
    #     if sudo -v; then
    #         if [[ $(sudo -H -- "${BASH}" -c 'printf "%s" "$EUID"') -eq 0 ]]; then
    #             _superuser=true
    #         else
    #             _superuser=false
    #         fi
    #     else
    #         _superuser=false
    #     fi
    # fi

    (_commandExists_ docker && _execute_ -s "docker --version" "docker check") || warning "docker check"

    if [[ ${_docker} == true ]]; then
        debug 'Docker available.'
        return 0
    else
        debug 'Docker not available.'
        return 1
    fi
}

_nmap_() {
    local stylesheet_url="https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl"
    local local_stylesheet="/tmp/nmap-bootstrap.xsl"
    local subnets=("${!CFG_NMAP_SUBNETS[@]}")
    local reports_dir="/tmp/nmap_reports"

    if [[ ! -f "$local_stylesheet" ]]; then
        _execute_ -vs "wget -O \"$local_stylesheet\" \"$stylesheet_url\""
    fi

    _execute_ -vs "mkdir -p \"$reports_dir\""
    _execute_ -vs "echo \"<!DOCTYPE html><html><head><style>table { font-family: arial, sans-serif; border-collapse: collapse; width: 30%; } td, th { border: 1px solid #dddddd; text-align: left; padding: 5px; } tr:nth-child(even) { background-color: #f2f2f2; }</style></head><body><h2>Nmap Reports</h2><table><tr><th>Subnet</th><th>IP Range</th><th>Execution Date</th><th>Report</th></tr>\" > \"$reports_dir/index.html\""

    for subnet in "${subnets[@]}"; do
        local xml_input="$reports_dir/${subnet}_map.xml"
        local html_output="$reports_dir/${subnet}_nmap_report.html"
        local subnet_ip_range="${CFG_NMAP_SUBNETS[$subnet]}"
        local nmap_opts="${CFG_NMAP_SUBNETS_OPTS[$subnet]:-${CFG_NMAP_OPTS}}"
        local execution_date=$(date "+%Y-%m-%d %H:%M:%S")

        _execute_ -vs "sudo nmap $nmap_opts --stylesheet \"$local_stylesheet\" -oX \"$xml_input\" \"$subnet_ip_range\""
        _execute_ -vs "xsltproc -o \"$html_output\" \"$local_stylesheet\" \"$xml_input\""

        _execute_ -vs "echo \"<tr><td>$subnet</td><td>$subnet_ip_range</td><td>$execution_date</td><td><a href='${subnet}_nmap_report.html'>Report</a></td></tr>\" >> \"$reports_dir/index.html\""
    done

    _execute_ -vs "echo \"</table></body></html>\" >> \"$reports_dir/index.html\""

    if pgrep -f "python3 -m http.server 8100" > /dev/null; then
        info "http.server already running"
        # pkill -f "python3 -m http.server 8100"
    else
        info "http.server not running, starting it"
        _execute_ -vs "cd \"$reports_dir\""
        _execute_ -vs "python3 -m http.server 8100 > /dev/null 2>&1 &"
    fi

    info "see the report at http://${CFG_SSH_CONTROLLER##*@}:8100/index.html"

    return 0
}

_installAnsible_() {
    # DESC:
    #         Validate docker is available
    # OUTS:
    #         0 if true
    #         1 if false

    debug "Python version: $(python3 -V)"

    _setv_create "${CFG_ANSIBLE_PACKAGE}-${CFG_TENANT}-${CFG_ANSIBLE_VERSION}"
    _setv_list
    setv "${CFG_ANSIBLE_PACKAGE}-${CFG_TENANT}-${CFG_ANSIBLE_VERSION}"

    # which python
    # which pip
    # export

    debug "Package ${CFG_ANSIBLE_PACKAGE}"
    debug "Install ${CFG_ANSIBLE_VERSION}"
    debug "Inventory ${CFG_ANSIBLE_INVENTORY}"
    debug "Playbook ${CFG_ANSIBLE_PLAYBOOK}"

    python3 -m pip install --upgrade pip
    python3 -m pip install ${CFG_ANSIBLE_PACKAGE}==${CFG_ANSIBLE_VERSION}
    python3 -m pip install jmespath
    python3 -m pip install six
    # python3 -m pip install ansible-runner
    # python3 -m pip list
    # ansible-galaxy collection list

    [ -n "${CFG_ANSIBLE_GALAXY_COLLECTIONS_REMOVE}" ] && \
        for _col in ${CFG_ANSIBLE_GALAXY_COLLECTIONS_REMOVE}; do
            _col_dir="${HOME}/.ansible/collections/ansible_collections/${_col%%.*}/${_col#*.}"
            [ -d "${_col_dir}" ] && rm -rf "${_col_dir}" && info "Removed collection ${_col}"
        done

    [ -n "${CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL}" ] && \
        ansible-galaxy collection install ${CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL}

    [ -n "${CFG_ANSIBLE_GALAXY_ROLES_REMOVE}" ] && \
        ansible-galaxy role remove ${CFG_ANSIBLE_GALAXY_ROLES_REMOVE}

    [ -n "${CFG_ANSIBLE_GALAXY_ROLES_INSTALL}" ] && \
        ansible-galaxy role install ${CFG_ANSIBLE_GALAXY_ROLES_INSTALL}

    # ansible-galaxy role list
    # ansible --version

    return 0
}

_checkoutFlameletTenantRepo_() {
    # DESC:
    #         Git checkout flamelet tenant repo
    # OUTS:
    #         0 if true
    #         1 if false
    local _path
    local _branch="${CFG_FLAMELET_TENANT_BRANCH:-origin/HEAD}"

    _path="${HOME}/.flamelet/tenant/flamelet-${_tenant}"
    # _path="\${HOME}/.flamelet/tenant"

    debug "Checkout ${CFG_FLAMELET_TENANT_REPO}"
    debug "Branch ${_branch}"

    _execute_ -vs "mkdir -p ${_path}"
    _execute_ -vs "cd ${_path}"
    # _execute_ -vs "ssh-add -L"

    export ANSIBLE_CONFIG=${CFG_ANSIBLE_CONFIG}

    if [ ! -d ".git" ]; then
        _execute_ -vs "git ${CFG_GIT_OPTIONS:+"$CFG_GIT_OPTIONS" }clone -b \"${_branch}\" \"${CFG_FLAMELET_TENANT_REPO}\" ."
    else
        _execute_ -vs "git ${CFG_GIT_OPTIONS:+"$CFG_GIT_OPTIONS" }fetch origin ${_branch}"
        _execute_ -vs "git ${CFG_GIT_OPTIONS:+"$CFG_GIT_OPTIONS" }checkout ${_branch}"
        _execute_ -vs "git ${CFG_GIT_OPTIONS:+"$CFG_GIT_OPTIONS" }pull origin ${_branch}"
        _execute_ -vs "git ${CFG_GIT_OPTIONS:+"$CFG_GIT_OPTIONS" }fetch --all"
        _execute_ -vs "git ${CFG_GIT_OPTIONS:+"$CFG_GIT_OPTIONS" }reset --hard ${_branch}"
    fi

    return 0
}

_checkVersion_() {
    # DESC:
    #         Check if a newer version of flamelet is available
    # OUTS:
    #         0 if check succeeded
    #         1 if unable to check
    local _localVersion="${FLAMELET_VERSION:-unknown}"
    local _remoteVersion=""
    local _remote="https://raw.githubusercontent.com/flameletlabs/flamelet/main/VERSION"

    if command -v curl &>/dev/null; then
        _remoteVersion="$(curl -fsSL --max-time 5 "${_remote}" 2>/dev/null)" || true
    elif command -v wget &>/dev/null; then
        _remoteVersion="$(wget -qO- --timeout=5 "${_remote}" 2>/dev/null)" || true
    fi

    _remoteVersion="${_remoteVersion//[$'\t\r\n ']}"

    if [[ -z "${_remoteVersion}" ]]; then
        warning "Unable to check for updates"
        return 1
    fi

    if [[ "${_localVersion}" == "${_remoteVersion}" ]]; then
        success "flamelet is up to date (${_localVersion})"
    else
        notice "Update available: ${_remoteVersion} (current: ${_localVersion})"
        notice "Run 'flamelet update' to upgrade"
    fi
    return 0
}

_updateFlamelet_() {
    # DESC:
    #         Update flamelet to the latest version from GitHub
    # OUTS:
    #         0 if true
    #         1 if false
    local _path
    local _remote="https://github.com/flameletlabs/flamelet.git"
    local _versionBefore="${FLAMELET_VERSION:-unknown}"
    local _versionAfter

    _path="${HOME}/.flamelet/bin"

    info "Current version: ${_versionBefore}"
    debug "Checkout ${_remote}"

    _execute_ -vs "mkdir -p ${_path}"
    _execute_ -vs "cd ${_path}"

    if [ ! -d ".git" ]; then
        _execute_ -vs "cd ${_path}/../"
        _execute_ -vs "rm -rf ${_path}"
        _execute_ -vs "mkdir -p ${_path}"
        _execute_ -vs "cd ${_path}"
        _execute_ -vs "git clone \"${_remote}\" ."
    else
        _execute_ -vs "git fetch --all"
        _execute_ -vs "git reset --hard origin/main"
    fi

    if [[ -f "${_path}/VERSION" ]]; then
        _versionAfter="$(< "${_path}/VERSION")"
    else
        _versionAfter="unknown"
    fi

    if [[ "${_versionBefore}" == "${_versionAfter}" ]]; then
        success "flamelet is already up to date (${_versionAfter})"
    else
        success "flamelet updated: ${_versionBefore} -> ${_versionAfter}"
    fi

    return 0
}

_ansible_() {
    # DESC:
    #         Run ansible command
    # OUTS:
    #         0 if true
    #         1 if false

    setv "${CFG_ANSIBLE_PACKAGE}-${CFG_TENANT}-${CFG_ANSIBLE_VERSION}"

    [[ -n "${_option}" ]] && _option="${_option:1:-1}"

    debug "option \"${_option}\""
    debug "ansible-playbook -i ${CFG_ANSIBLE_INVENTORY} ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } ${_option:+$_option } ${CFG_ANSIBLE_PLAYBOOK}"

    _execute_ -vs "\
        ANSIBLE_CONFIG=${CFG_ANSIBLE_CONFIG:-/etc/ansible/ansible.cfg} ansible-playbook -i ${CFG_ANSIBLE_INVENTORY} ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } ${_option:+$_option } ${CFG_ANSIBLE_PLAYBOOK}"

    deactivate
    # _setv_delete_force "test"

    return 0
}

_ansibleModule_() {
    # DESC:
    #   Execute an Ansible command using options passed via -o.
    #   Allows full control of the Ansible module and arguments through raw input.
    # ARGS:
    #   None (uses globally available CFG variables for tenant and options).
    # OUTS:
    #   Executes the specified Ansible command and prints results.

    setv "${CFG_ANSIBLE_PACKAGE}-${CFG_TENANT}-${CFG_ANSIBLE_VERSION}"

    # Extract raw options from _option and remove surrounding quotes
    local raw_options=""
    [[ -n "${_option}" ]] && raw_options="${_option:1:-1}"

    debug "Raw Options: ${raw_options}"
    debug "Command: ansible -o -i ${CFG_ANSIBLE_INVENTORY} ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } ${raw_options}"

    # Execute the Ansible command with raw options
    _execute_ -vs "\
        ANSIBLE_CONFIG=${CFG_ANSIBLE_CONFIG:-/etc/ansible/ansible.cfg} \
        ansible -o -i ${CFG_ANSIBLE_INVENTORY} \
        ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } \
        ${raw_options}"

    # Cleanup
    deactivate

    return 0
}

_doctor_() {
    # DESC:
    #         Run health checks on flamelet and tenant configuration
    # OUTS:
    #         0 always (individual checks may fail without aborting)

    header "flamelet doctor"

    # Global checks (always)
    _checkVersion_ || true
    _doctorStaleVenvs_ || true

    # Tenant-specific checks (only with -t)
    if ! _varIsFalse_ "${TENANT}"; then
        notice "Tenant: ${CFG_TENANT}"

        [[ -n "${CFG_ANSIBLE_PACKAGE}" && -n "${CFG_ANSIBLE_VERSION}" ]] && \
            _doctorAnsibleVersion_ || true

        [[ -n "${CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL}" ]] && \
            _doctorUnusedCollections_ || true

        [[ -n "${CFG_ANSIBLE_GALAXY_ROLES_INSTALL}" ]] && \
            _doctorUnusedRoles_ || true
    else
        info "No tenant specified; use 'flamelet -t <tenant> doctor' for full diagnostics"
    fi
}

_doctorStaleVenvs_() {
    # DESC:
    #         Find and optionally clean up stale virtual environments
    # OUTS:
    #         0 if check succeeded
    #         1 if venv directory does not exist
    local _venvDir="${SETV_VIRTUAL_DIR_PATH}"
    local -a _expectedVenvs=()
    local -a _staleVenvs=()
    local _tenantDir
    local _venvName

    header "Stale virtual environments"

    if ! (_isDir_ "${_venvDir}"); then
        info "No venv directory found at ${_venvDir}"
        return 0
    fi

    # Collect expected venv names from all tenant configs
    for _tenantDir in "${HOME}"/.flamelet/tenant/flamelet-*/; do
        [[ -d "${_tenantDir}" ]] || continue
        if [[ -f "${_tenantDir}/config.sh" ]]; then
            _venvName=$(
                local CFG_ANSIBLE_PACKAGE=""
                local CFG_TENANT=""
                local CFG_ANSIBLE_VERSION=""
                # shellcheck disable=SC1091
                source "${_tenantDir}/config.sh" 2>/dev/null
                if [[ -n "${CFG_ANSIBLE_PACKAGE}" && -n "${CFG_TENANT}" && -n "${CFG_ANSIBLE_VERSION}" ]]; then
                    printf "%s" "${CFG_ANSIBLE_PACKAGE}-${CFG_TENANT}-${CFG_ANSIBLE_VERSION}"
                fi
            ) || true
            [[ -n "${_venvName}" ]] && _expectedVenvs+=("${_venvName}")
        fi
    done

    debug "Expected venvs: ${_expectedVenvs[*]:-none}"

    # Compare actual venvs against expected
    for _dir in "${_venvDir}"*/; do
        [[ -d "${_dir}" ]] || continue
        _venvName="$(basename "${_dir}")"
        local _found=false
        for _expected in "${_expectedVenvs[@]:-}"; do
            if [[ "${_venvName}" == "${_expected}" ]]; then
                _found=true
                break
            fi
        done
        if [[ "${_found}" == false ]]; then
            _staleVenvs+=("${_venvName}")
        fi
    done

    if [[ ${#_staleVenvs[@]} -eq 0 ]]; then
        success "No stale virtual environments found"
        return 0
    fi

    warning "Found ${#_staleVenvs[@]} stale virtual environment(s):"
    for _venvName in "${_staleVenvs[@]}"; do
        info "  ${_venvDir}${_venvName}"
    done

    if _seekConfirmation_ "Delete stale virtual environments?"; then
        for _venvName in "${_staleVenvs[@]}"; do
            _execute_ -vs "rm -rf \"${_venvDir}${_venvName}\"" \
                "Remove stale venv: ${_venvName}"
        done
        success "Stale virtual environments cleaned up"
    else
        info "Skipped cleanup"
    fi

    return 0
}

_doctorAnsibleVersion_() {
    # DESC:
    #         Check PyPI for newer versions of the configured Ansible package
    # OUTS:
    #         0 if check succeeded
    #         1 if unable to check
    local _package="${CFG_ANSIBLE_PACKAGE}"
    local _currentVersion="${CFG_ANSIBLE_VERSION}"
    local _pypiUrl="https://pypi.org/pypi/${_package}/json"
    local _json=""
    local _latestStable=""
    local _latestInSeries=""
    local _currentMajorMinor=""

    header "Ansible version check"

    info "Current: ${_package}==${_currentVersion}"

    # Fetch PyPI metadata
    if command -v curl &>/dev/null; then
        _json="$(curl -fsSL --max-time 10 "${_pypiUrl}" 2>/dev/null)" || true
    elif command -v wget &>/dev/null; then
        _json="$(wget -qO- --timeout=10 "${_pypiUrl}" 2>/dev/null)" || true
    fi

    if [[ -z "${_json}" ]]; then
        warning "Unable to fetch version info from PyPI"
        return 1
    fi

    # Extract latest stable version and latest in current major.minor series
    _currentMajorMinor="${_currentVersion%.*}"
    read -r _latestStable _latestInSeries < <(
        python3 -c "
import json, sys, re
data = json.loads(sys.stdin.read())
latest = data.get('info', {}).get('version', '')
releases = [k for k in data.get('releases', {}).keys()
            if re.match(r'^[0-9]+\.[0-9]+\.[0-9]+$', k)]
series = '${_currentMajorMinor}'
in_series = sorted(
    [v for v in releases if v.startswith(series + '.')],
    key=lambda v: list(map(int, v.split('.')))
)
latest_in_series = in_series[-1] if in_series else ''
print(latest, latest_in_series)
" <<< "${_json}" 2>/dev/null
    ) || true

    if [[ -z "${_latestStable}" ]]; then
        warning "Unable to parse PyPI response"
        return 1
    fi

    info "Latest stable: ${_package}==${_latestStable}"

    if [[ -n "${_latestInSeries}" && "${_latestInSeries}" != "${_currentVersion}" ]]; then
        notice "Newer patch: ${_package} ${_latestInSeries} available in ${_currentMajorMinor}.x series"
    elif [[ -n "${_latestInSeries}" ]]; then
        success "Up to date in ${_currentMajorMinor}.x series"
    fi

    if [[ "${_latestStable}" != "${_currentVersion}" && "${_latestStable}" != "${_latestInSeries}" ]]; then
        notice "Major/minor upgrade available: ${_package}==${_latestStable}"
    fi

    return 0
}

_doctorUnusedCollections_() {
    # DESC:
    #         Find Galaxy collections that are installed but not referenced in tenant YAML files
    # OUTS:
    #         0 if check succeeded
    local -a _collections
    local _collection
    local _tenantPath="${HOME}/.flamelet/tenant/flamelet-${TENANT}"
    local -a _unusedCollections=()

    header "Unused Galaxy collections"

    read -ra _collections <<< "${CFG_ANSIBLE_GALAXY_COLLECTIONS_INSTALL}"

    if [[ ${#_collections[@]} -eq 0 ]]; then
        info "No collections configured"
        return 0
    fi

    if ! (_isDir_ "${_tenantPath}"); then
        warning "Tenant directory not found: ${_tenantPath}"
        return 1
    fi

    for _collection in "${_collections[@]}"; do
        # Skip empty entries from whitespace splitting
        [[ -z "${_collection}" ]] && continue
        # Escape dots for grep pattern
        local _pattern="${_collection//./\\.}"
        # Search for FQCN usage (e.g. community.docker.docker_container)
        # or collection name in collections: declarations
        if ! grep -rq --include="*.yml" --include="*.yaml" \
            -e "${_pattern}\." -e "${_pattern}" \
            "${_tenantPath}/" 2>/dev/null; then
            _unusedCollections+=("${_collection}")
        fi
    done

    if [[ ${#_unusedCollections[@]} -eq 0 ]]; then
        success "All ${#_collections[@]} collections are referenced in tenant files"
    else
        warning "Found ${#_unusedCollections[@]} potentially unused collection(s):"
        for _collection in "${_unusedCollections[@]}"; do
            info "  ${_collection}"
        done
        info "Review before removing — comments and dynamic includes may reference them"
    fi

    return 0
}

_doctorUnusedRoles_() {
    # DESC:
    #         Find Galaxy roles that are installed but not referenced in tenant YAML files
    # OUTS:
    #         0 if check succeeded
    local -a _roles
    local _role
    local _roleName
    local _tenantPath="${HOME}/.flamelet/tenant/flamelet-${TENANT}"
    local -a _unusedRoles=()

    header "Unused Galaxy roles"

    read -ra _roles <<< "${CFG_ANSIBLE_GALAXY_ROLES_INSTALL}"

    if [[ ${#_roles[@]} -eq 0 ]]; then
        info "No roles configured"
        return 0
    fi

    if ! (_isDir_ "${_tenantPath}"); then
        warning "Tenant directory not found: ${_tenantPath}"
        return 1
    fi

    for _role in "${_roles[@]}"; do
        # Skip empty entries from whitespace splitting
        [[ -z "${_role}" ]] && continue
        # Strip version pin (e.g. hspaans.package,v1.0.4 -> hspaans.package)
        _roleName="${_role%%,*}"
        # Search for role usage: role: <name>, - <name>, include_role/import_role name: <name>
        if ! grep -rq --include="*.yml" --include="*.yaml" \
            -e "${_roleName}" \
            "${_tenantPath}/" 2>/dev/null; then
            _unusedRoles+=("${_roleName}")
        fi
    done

    if [[ ${#_unusedRoles[@]} -eq 0 ]]; then
        success "All ${#_roles[@]} roles are referenced in tenant files"
    else
        warning "Found ${#_unusedRoles[@]} potentially unused role(s):"
        for _roleName in "${_unusedRoles[@]}"; do
            info "  ${_roleName}"
        done
        info "Review before removing — comments and dynamic includes may reference them"
    fi

    return 0
}
