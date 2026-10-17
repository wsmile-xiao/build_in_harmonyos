#!/data/service/hnp/bin/bash
# Consumer checks for scanlogd 2.2.8.
set -eu

SCANLOGD_BIN="${SCANLOGD_BIN:-scanlogd}"
SCANLOGD_PREFIX="${SCANLOGD_PREFIX:-}"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

[ -x "$SCANLOGD_BIN" ] || fail "installed scanlogd is missing or not executable"
echo "PASS: installed scanlogd binary is executable"

if [ -n "$SCANLOGD_PREFIX" ]; then
    [ -s "$SCANLOGD_PREFIX/share/man/man8/scanlogd.8" ] \
        || fail "installed scanlogd.8 manual page is missing"
    echo "PASS: installed scanlogd.8 manual page is present"

    [ -s "$SCANLOGD_PREFIX/etc/scanlogd.init" ] \
        || fail "installed scanlogd.init service template is missing"
    echo "PASS: installed scanlogd.init service template is present"
fi

check_cli_success() {
    label="$1"
    expected="$2"
    shift 2

    set +e
    output=$("$SCANLOGD_BIN" "$@" 2>&1)
    status=$?
    set -e

    [ "$status" -eq 0 ] \
        || fail "$label expected exit status 0, got $status: $output"
    printf '%s\n' "$output" | grep -F "$expected" >/dev/null \
        || fail "$label output did not contain: $expected"
    echo "PASS: $label exits 0 and reports $expected"
}

check_unknown_option() {
    set +e
    output=$("$SCANLOGD_BIN" --definitely-invalid-option 2>&1)
    status=$?
    set -e

    [ "$status" -eq 2 ] \
        || fail "unknown option expected exit status 2, got $status: $output"
    printf '%s\n' "$output" | grep -F "unknown option" >/dev/null \
        || fail "unknown option did not report an argument error: $output"
    echo "PASS: unknown option exits 2 with an argument error"
}

check_cli_success "--help" "Usage: scanlogd" --help
check_cli_success "--version" "scanlogd 2.2.8" --version
check_unknown_option

if [ "$(id -u)" -eq 0 ]; then
    echo "SKIP: raw-socket permission failure check under root (not reported as PASS)"
    exit 0
fi

check_expected_permission_failure() {
    label="$1"
    shift

    set +e
    output=$("$SCANLOGD_BIN" "$@" 2>&1)
    status=$?
    set -e

    [ "$status" -eq 1 ] \
        || fail "$label expected exit status 1, got $status: $output"
    echo "PASS: $label exits with expected status 1"

    case "$output" in
        "socket: Operation not permitted"*|"socket: Permission denied"*)
            echo "PASS: $label reports the expected raw-socket permission error"
            ;;
        *)
            fail "$label did not report an accepted socket permission error: $output"
            ;;
    esac
}

# No arguments still exercises the upstream raw-socket initialization path. It
# must fail predictably without privileges and is skipped under root.
check_expected_permission_failure "no-argument daemon path"

echo "scanlogd consumer checks completed"
