#!/usr/bin/env bash
# ACD HW2 self-check. Same shape as HW1's verify_hw1.sh.
#
#   bash verify_hw2.sh <student-id> info
#   bash verify_hw2.sh <student-id> test
#
# `info` prints the environment and a checksum and listing of your
# local_dce.py. `test` runs the public test cases with the same evaluator
# the TAs use and prints a score summary.

set -u
set -o pipefail

usage() {
    echo "Usage:"
    echo "  bash verify_hw2.sh <student_id> info"
    echo "  bash verify_hw2.sh <student_id> test"
}

if [[ $# -ne 2 ]]; then
    usage
    exit 1
fi

STUDENT_ID="$1"
MODE="$2"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTRY="$REPO_ROOT/src/local_dce.py"

print_identity() {
    echo "============================================================"
    echo "ACD HW2 Verification"
    echo "============================================================"
    echo "Student ID        : $STUDENT_ID"
    echo "Timestamp         : $(date -Iseconds)"
    echo "Working directory : $(pwd)"
    echo
}

print_system_info() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "Operating system  : ${PRETTY_NAME:-unknown}"
    else
        echo "Operating system  : unknown"
    fi
    echo "Architecture      : $(uname -m)"
    echo "Python            : $(python3 --version 2>&1)"
    echo "bril2json         : $(command -v bril2json || echo NOT FOUND)"
    echo "brili             : $(command -v brili || echo NOT FOUND)"
}

require_tools() {
    local missing=0 tool
    for tool in bril2json bril2txt brili python3; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo "ERROR: $tool is not on PATH."
            missing=1
        fi
    done
    if [[ "$missing" -ne 0 ]]; then
        echo
        echo "Run this script inside the HW2 container, where the Bril tools"
        echo "are already installed:"
        echo "  docker run -it --rm -v \"\$PWD\":/home/student/hw acd-hw2:2026"
        exit 1
    fi
}

run_info() {
    print_identity
    print_system_info
    echo
    echo "---------------- src/local_dce.py ----------------"
    if [[ ! -f "$ENTRY" ]]; then
        echo "ERROR: src/local_dce.py not found."
        exit 1
    fi
    echo
    echo "SHA256:"
    sha256sum "$ENTRY"
    echo
    echo "Other files you added in src/:"
    find "$REPO_ROOT/src" -maxdepth 1 -name '*.py' \
        ! -name local_dce.py ! -name lvn.py \
        ! -name form_blocks.py ! -name util.py -printf '  %f\n' 2>/dev/null \
        | sort
    echo
    echo "Contents:"
    nl -ba "$ENTRY"
    echo
    echo "---------------- End of info output ----------------"
}

run_test() {
    print_identity
    print_system_info
    require_tools

    if [[ ! -f "$ENTRY" ]]; then
        echo "ERROR: src/local_dce.py not found."
        exit 1
    fi

    echo
    echo "src/local_dce.py SHA256:"
    sha256sum "$ENTRY"

    echo
    python3 "$REPO_ROOT/tools/selfcheck.py"
    exit $?
}

case "$MODE" in
    info) run_info ;;
    test) run_test ;;
    *) usage; exit 1 ;;
esac
