#!/usr/bin/env bash
# Bash is required for local variables and strict consumer assertions.
set -euo pipefail

check_help() {
    local command_name="$1"
    local expected_status="$2"
    local expected_text="$3"
    local output
    local status
    set +e
    output=$("$command_name" --help 2>&1)
    status=$?
    set -e
    [ "$status" -eq "$expected_status" ]
    printf '%s\n' "$output" | grep -Fq "$expected_text"
}

check_version() {
    local output
    output=$(exult --version 2>&1)
    printf '%s\n' "$output" | grep -Fq "Exult version 1.12.1"
}

check_version
check_help expack 0 "Usage:"
check_help ipack 1 "Usage: ipack"
printf '%s\n' 'consumer smoke test passed: exult, expack, and ipack respond'
