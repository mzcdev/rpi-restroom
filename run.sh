#!/bin/bash

SHELL_DIR=$(dirname $0)

CMD=${1:-init}

CONFIG=~/.rpi-restroom
touch ${CONFIG}
. ${CONFIG}

command -v tput > /dev/null || TPUT=false

_echo() {
    if [ -z ${TPUT} ] && [ ! -z $2 ]; then
        echo -e "$(tput setaf $2)$1$(tput sgr0)"
    else
        echo -e "$1"
    fi
}

_read() {
    if [ -z ${TPUT} ]; then
        read -p "$(tput setaf 6)$1$(tput sgr0)" ANSWER
    else
        read -p "$1" ANSWER
    fi
}

_result() {
    _echo "# $@" 4
}

_command() {
    _echo "$ $@" 3
}

_success() {
    _echo "+ $@" 2
    exit 0
}

_error() {
    _echo "- $@" 1
    exit 1
}

_status() {
    PID=$(ps -ef | grep python3 | grep " sonic[.]py" | head -1 | awk '{print $2}' | xargs)
    if [ "${PID}" != "" ]; then
        _result "rpi-restroom is running: ${PID}"
    else
        _result "rpi-restroom is stopped"
    fi
}

_stop() {
    if [ "${PID}" == "" ]; then
        return
    fi

    _command "kill -9 ${PID}"
    kill -9 ${PID}

    _status
}

_start() {
    if [ "${PID}" != "" ]; then
        return
    fi

    pushd ${SHELL_DIR}
    _command "python3 sonic.py"
    # nohup python3 sonic.py > log.out 2>&1 &
    nohup python3 sonic.py > /dev/null 2>&1 &
    popd

    _status
}

_log() {
    tail -f ${SHELL_DIR}/log.out
}

_config_read() {
    if [ -z ${REMOTE_URL} ]; then
        _read "REMOTE_URL [${REMOTE_URL}]: " "${REMOTE_URL}"
        if [ ! -z ${ANSWER} ]; then
            REMOTE_URL="${ANSWER}"
        fi
    fi

    export REMOTE_URL="${REMOTE_URL}"
}

_config_save() {
    echo "# rpi-restroom config" > ${CONFIG}
    echo "export REMOTE_URL=${REMOTE_URL}" >> ${CONFIG}

    cat ${CONFIG}
}

_init() {
    pushd ${SHELL_DIR}
    git pull
    popd
}

# _config_read
# _config_save

case ${CMD} in
    init)
        _init
        _status
        _stop
        _start
        ;;
    status)
        _status
        ;;
    start)
        _status
        _stop
        _start
        ;;
    stop)
        _status
        _stop
        ;;
    log)
        _log
        ;;
esac
