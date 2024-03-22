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
            _runAsRoot_ pkg install -y bash tree rsync git-lite tmux ccze ncdu wget python310 nmap libxslt
            _runAsRoot_ ln -fs /usr/local/bin/python3.10 /usr/local/bin/python3
            return 0
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
        ansible-galaxy collection remove ${CFG_ANSIBLE_GALAXY_COLLECTIONS_REMOVE}

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

_updateFlamelet_() {
    # DESC:
    #         Git checkout flamelet app repo
    # OUTS:
    #         0 if true
    #         1 if false
    local _path
    local _remote="https://github.com/flameletlabs/flamelet.git"

    _path="${HOME}/.flamelet/bin"
    # _path="\${HOME}/.flamelet/tenant"

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

    return 0
}

_ansible_() {
    # DESC:
    #         Run ansible command
    # OUTS:
    #         0 if true
    #         1 if false

    setv "${CFG_ANSIBLE_PACKAGE}-${CFG_TENANT}-${CFG_ANSIBLE_VERSION}"

    _option="${_option:1:-1}"

    debug "option \"${_option}\""
    debug "ansible-playbook -i ${CFG_ANSIBLE_INVENTORY} ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } ${_option:+$_option } ${CFG_ANSIBLE_PLAYBOOK}"

    _execute_ -vs "\
        ANSIBLE_CONFIG=${CFG_ANSIBLE_CONFIG:-/etc/ansible/ansible.cfg} ansible-playbook -i ${CFG_ANSIBLE_INVENTORY} ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } ${_option:+$_option } ${CFG_ANSIBLE_PLAYBOOK}"

    deactivate
    # _setv_delete_force "test"

    return 0
}
