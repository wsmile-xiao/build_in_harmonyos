#!/bin/sh
set -eu

BIN_DIR=$1

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

[ -d "$BIN_DIR" ] || fail "package bin directory is missing: $BIN_DIR"

run_expect() {
    expected_code=$1
    expected_output=$2
    shift 2

    set +e
    actual_output=$("$@" 2>&1)
    actual_code=$?
    set -e

    [ "$actual_code" -eq "$expected_code" ] || \
        fail "$* returned $actual_code, expected $expected_code"
    [ "$actual_output" = "$expected_output" ] || \
        fail "$* output '$actual_output', expected '$expected_output'"
}

run_version() {
    plugin=$1
    path="$BIN_DIR/$plugin"
    [ -x "$path" ] || fail "plugin is missing or not executable: $path"

    set +e
    output=$("$path" --version 2>&1)
    code=$?
    set -e

    [ "$code" -eq 0 ] || fail "$plugin --version returned $code"
    case "$output" in
        *2.5*) ;;
        *) fail "$plugin version output does not contain 2.5: $output" ;;
    esac
}

run_expect 0 "OK: consumer-ok" "$BIN_DIR/check_dummy" 0 consumer-ok
run_expect 2 "CRITICAL: consumer-critical" \
    "$BIN_DIR/check_dummy" 2 consumer-critical

run_version check_tcp
run_version check_udp
run_version check_disk
run_version check_http
run_version check_simap

echo "PASS: nagios-plugins consumer checks"
