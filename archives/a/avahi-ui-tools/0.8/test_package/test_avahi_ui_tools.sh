#!/bin/sh
# Consumer harness for avahi-ui-tools 0.8.
# Usage: sh test_avahi_ui_tools.sh <package_bin_dir> <result_file>
#
# bssh is a GTK3 service-browsing dialog: real browsing needs a live
# avahi-daemon and an interactive session, which is out of scope for a
# consumer test.  We verify the offline contract that is headless-safe:
#   - bssh / bvnc / bshell are all present (bvnc/bshell are the upstream
#     symlink aliases of bssh; fallback copies are equally acceptable)
#   - an unknown long option makes bssh print its usage to stderr and
#     exit non-zero *before* gtk_init runs (bssh.c parses the command
#     line first and returns early on parse failure)
# Writes "discovered N" / "passed M" lines to <result_file> and exits 0
# iff every assertion passed. No set -e: expected-failure cases rely on rc.
set -u

BIN_DIR=${1:?usage: test_avahi_ui_tools.sh <package_bin_dir> <result_file>}
RESULT_FILE=${2:?usage: test_avahi_ui_tools.sh <package_bin_dir> <result_file>}
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
        return 0
    else
        echo "FAIL: $desc (rc=$rc)"
        printf '%s\n' "$out" | sed -n '1,5p'
        return 1
    fi
}

# bssh/bvnc/bshell must be present.  bvnc/bshell are the upstream symlink
# aliases of bssh (fallback copies equally acceptable), so use `test -e`
# which matches both regular files and symlinks in a single assertion
# (avoiding the double-count that a `||` fallback would introduce).
for tool in bssh bvnc bshell; do
    run_case "$tool is packaged and present" \
        yes "" test -e "$BIN_DIR/$tool"
done

# bssh must be an executable ELF.
run_case "bssh is executable" yes "" test -x "$BIN_DIR/bssh"

# Unknown option: parse_command_line() fails before gtk_init, so this is
# headless-safe; expect non-zero exit and the usage text on stderr.
run_case "bssh rejects an unknown long option (pre-gtk_init path)" \
    no "[options]" "$BIN_DIR/bssh" --this-option-does-not-exist

printf 'discovered %d\npassed %d\n' "$discovered" "$passed" > "$RESULT_FILE"
cat "$RESULT_FILE"

[ "$passed" -eq "$discovered" ]