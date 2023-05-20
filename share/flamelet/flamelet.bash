# Flamelet functions

sshqfunc() { echo "bash -c $(printf "%q" "$(declare -f "$@"); $1 \"\$@\"")"; };

_cleanOptions_() {

    declare -a _options=("$@")
    declare -a _cleanedOptions
    local _option

    for _option in "${_options[@]}"; do 
        [[ ! $"${_option}" == '-r' ]] && [[ ! $"${_option}" == '--remote' ]] && \
        _cleanedOptions+=("${_option}")
    done

    printf '%s\n' "${_cleanedOptions[@]}"
}

_installRemote_() {
    local _path _files

    _path=".flamelet/bin"
    _files="alerts.bash,arrays.bash,checks.bash,debug.bash,files.bash,setv.bash,flamelet.bash,misc.bash,template_utils.bash"

    _execute_ -vs "ssh ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }-T ${CFG_SSH_CONTROLLER}" "Cleanup" <<-EOF
    mkdir -p ${_path}/share/flamelet
    mkdir -p \${HOME}/.flamelet
    rm -f ${_path}/share/flamelet/*.bash
    rm -f ${_path}/flamelet
    rm -f ${HOME}/.flamelet/env.sh
EOF

    _execute_ -vs "scp -q -B -C ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }\
$(_findBaseDir_)/../../flamelet ${CFG_SSH_CONTROLLER}:\${_path}/flamelet" \
"Install flamelet script"

    _execute_ -vs "scp -q -B -C ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }\
$(_findBaseDir_)/{${_files}} ${CFG_SSH_CONTROLLER}:\${_path}/share/flamelet/" \
"Install flamelet libraries"

    (_isFile_ "${HOME}/.flamelet/tenant/flamelet-${_tenant}/env.sh") && \
        _execute_ -vs "scp -q -B -C ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }\
${HOME}/.flamelet/tenant/flamelet-${_tenant}/env.sh ${CFG_SSH_CONTROLLER}:\${HOME}/.flamelet/env.sh" \
"Install environment" || \
info "Environment not defined"
}

_installDeps_() {

    local _cmd=()

    case $(_detectOS_) in
        linux)
            case $(_detectLinuxDistro_) in
                debian* | ubuntu)
                    _cmd=( env DEBIAN_FRONTEND=noninteractive apt-get -y install bash tree rsync git tmux ccze ncdu virt-what python3 python3-venv sshpass )
                    ;;
                centos*)
                    _cmd=( yum -y install bash hostname tree rsync git tmux ccze ncdu python3 )
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
            _cmd=( pkg install -y bash tree rsync git-lite tmux ccze ncdu )
            ;;
        openbsd)
            _cmd=( pkg_add -U -I bash tree rsync-- git python3 rust )
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

    (_commandExists_ python3 && _execute_ -s "python3 -V" "python3 check") || warning "python3 check"
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

    _execute_ -vs "ssh ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }-q -t ${CFG_SSH_CONTROLLER} \
\"bash -c '\${_path}/flamelet ${_remoteOptions}'\"" \
"Running '\${_path}/flamelet ${_remoteOptions}' via ssh on '${CFG_SSH_CONTROLLER}'"

# WORKS: CFG_ENV_CONTROLLER="function foo() { uname; }" ; assh sockets flush ; \
#   ssh -q -t localhost "bash -c '$CFG_ENV_CONTROLLER ; foo'"

#    _execute_ -vs "ssh ${CFG_SSH_OPTIONS:+"$CFG_SSH_OPTIONS" }-q -t ${CFG_SSH_CONTROLLER} \
# \"bash -c '$CFG_ENV_CONTROLLER ; python3 -V'\"" \
# "Running '\${_path}/flamelet ${_remoteOptions}' via ssh on '${CFG_SSH_CONTROLLER}'"
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

_installAnsible_() {
    # DESC:
    #         Validate docker is available
    # OUTS:
    #         0 if true
    #         1 if false

    # will be: flamelet-ansible-6.1.0
    _setv_create "ansible-${CFG_ANSIBLE_VERSION}"
    _setv_list
    setv "ansible-${CFG_ANSIBLE_VERSION}"

    # which python
    # which pip

    debug "Install ${CFG_ANSIBLE_VERSION}"
    debug "Inventory ${CFG_ANSIBLE_INVENTORY}"
    debug "Playbook ${CFG_ANSIBLE_PLAYBOOK}"

    python3 -m pip install --upgrade pip
    python3 -m pip install ansible==${CFG_ANSIBLE_VERSION}
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

    _path="${HOME}/.flamelet/tenant/flamelet-${_tenant}"
    # _path="\${HOME}/.flamelet/tenant"

    debug "Checkout ${CFG_FLAMELET_TENANT_REPO}"

    _execute_ -vs "mkdir -p ${_path}"
    _execute_ -vs "cd ${_path}"
    # _execute_ -vs "ssh-add -L"

    if [ ! -d ".git" ]; then
        _execute_ -vs "git clone \"${CFG_FLAMELET_TENANT_REPO}\" ."
    else
        _execute_ -vs "git fetch --all"
        _execute_ -vs "git reset --hard origin/HEAD"
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
    local _remote=${REMOTE:-https://github.com/flameletlabs/flamelet.git}

    _path="${HOME}/.flamelet/bin"
    # _path="\${HOME}/.flamelet/tenant"

    debug "Checkout ${REMOTE}"

    _execute_ -vs "mkdir -p ${_path}"
    _execute_ -vs "cd ${_path}"

    if [ ! -d ".git" ]; then
        _execute_ -vs "git clone \"${REMOTE}\" ."
    else
        _execute_ -vs "git fetch --all"
        _execute_ -vs "git reset --hard origin/HEAD"
    fi

    return 0
}

_ansible_() {
    # DESC:
    #         Run ansible command
    # OUTS:
    #         0 if true
    #         1 if false

    setv "ansible-${CFG_ANSIBLE_VERSION}"
    
    export ANSIBLE_CONFIG=${CFG_ANSIBLE_CONFIG}

    _execute_ -vs "\
        ansible-playbook -i ${CFG_ANSIBLE_INVENTORY} ${CFG_ANSIBLE_OPTIONS:+$CFG_ANSIBLE_OPTIONS } ${_option:+$_option } ${CFG_ANSIBLE_PLAYBOOK}"
    
    deactivate
    # _setv_delete_force "test"

    return 0
}
