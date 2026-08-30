#!/bin/sh
# Consumer harness for avahi-tools 0.9_rc5.
# Usage: sh test_avahi_tools.sh <package_bin_dir> <result_file>
#
# Exercises the offline CLI contract of the four packaged utilities:
#   - --help exits 0 and prints the "-h --help" usage line
#   - --version exits 0 and prints the upstream version "0.9-rc5"
#   - unknown options and missing required arguments fail with non-zero exit
# (browse/resolve/publish/set-host-name need a live avahi-daemon on the D-Bus
# system bus for their actual work, which is out of scope for a consumer test.)
# Writes "discovered N" / "passed M" lines to <result_file> and exits 0 iff
# every assertion passed. No set -e: expected-failure cases rely on rc checks.
set -u

BIN_DIR=${1:?usage: test_avahi_tools.sh <package_bin_dir> <result_file>}
RESULT_FILE=${2:?usage: test_avahi_tools.sh <package_bin_dir> <result_file>}
discovered=0
passed=0

run_case() {
    # run_case <description> <expect_ok: yes|no> <pattern> <cmd...>
    desc=$1
    expect_ok=$2
    pattern=$3
    shift 3
    out=$("$@" 2>&1)
    rc=$?
    discovered=$((discovered + 1))
    ok=1
    if [ "$expect_ok" = yes ] && [ "$rc" -ne 0 ]; then
        ok=0
    fi
    if [ "$expect_ok" = no ] && [ "$rc" -eq 0 ]; then
        ok=0
    fi
    if [ -n "$pattern" ]; then
        case "$out" in
            *"$pattern"*) ;;
            *) ok=0 ;;
        esac
    fi
    if [ "$ok" -eq 1 ]; then
        passed=$((passed + 1))
        echo "PASS: $desc"
    else
        echo "FAIL: $desc (rc=$rc)"
        printf '%s\n' "$out" | sed -n '1,5p'
    fi
}

for tool in avahi-browse avahi-resolve avahi-publish avahi-set-host-name; do
    run_case "$tool --help prints usage and exits 0" \
        yes "-h --help" "$BIN_DIR/$tool" --help
    run_case "$tool --version prints 0.9-rc5 and exits 0" \
        yes "0.9-rc5" "$BIN_DIR/$tool" --version
done

run_case "avahi-browse rejects an unknown long option" \
    no "" "$BIN_DIR/avahi-browse" --this-option-does-not-exist
run_case "avahi-set-host-name rejects a missing argument" \
    no "" "$BIN_DIR/avahi-set-host-name"

printf 'discovered %d\npassed %d\n' "$discovered" "$passed" > "$RESULT_FILE"
cat "$RESULT_FILE"

[ "$passed" -eq "$discovered" ]
