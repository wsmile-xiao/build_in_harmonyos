#!/usr/bin/env bash
# Runtime tests against the binaries delivered by this package.
set -euo pipefail

PKG="${1:?usage: test_cli.sh <package_folder>}"
TARGET="${2:-}"
BIN="$PKG/bin"
PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); echo "[ok] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "[FAIL] $1"; }

check_elf() {
    local name="$1" path="$BIN/$1" magic
    if [ -x "$path" ]; then ok "$name exists and is executable"; else bad "$name missing/not executable"; return; fi
    magic=$(od -An -tx1 -N4 "$path" 2>/dev/null | tr -d ' \n')
    if [ "$magic" = "7f454c46" ]; then ok "$name has ELF magic"; else bad "$name is not ELF"; fi
    # HarmonyOS PC packages target little-endian AArch64 (ELF e_machine = 183).
    set -- $(od -An -tu1 -j18 -N2 "$path" 2>/dev/null)
    if [ "$#" -eq 2 ] && [ "$(( $1 + ($2 << 8) ))" -eq 183 ]; then
        ok "$name targets HarmonyOS PC AArch64 ELF ABI"
    else
        bad "$name is not an AArch64 ELF (e_machine=$*)"
    fi
}

run_capture() {
    local output_file
    if ! output_file=$(mktemp); then
        echo "[FAIL] unable to create temporary capture file" >&2
        return 2
    fi
    if "$@" >"$output_file" 2>&1; then RC=0; else RC=$?; fi
    OUT=$(cat "$output_file")
    rm -f "$output_file"
}

check_elf jool
check_elf jool_siit
check_elf joold

run_capture "$BIN/jool" --version
[ "$RC" -eq 0 ] && ok "jool --version exits successfully" || bad "jool --version exit=$RC"
[ "$OUT" = "4.1.14.0" ] && ok "jool reports upstream version 4.1.14.0" || bad "jool version output: $OUT"

run_capture "$BIN/jool_siit" --version
[ "$RC" -eq 0 ] && ok "jool_siit --version exits successfully" || bad "jool_siit --version exit=$RC"
[ "$OUT" = "4.1.14.0" ] && ok "jool_siit reports upstream version 4.1.14.0" || bad "jool_siit version output: $OUT"

run_capture "$BIN/jool" --help
[ "$RC" -eq 0 ] && ok "jool --help exits successfully" || bad "jool --help exit=$RC"
case "$OUT" in *Usage*) ok "jool --help prints usage" ;; *) bad "jool --help has no usage" ;; esac
case "$OUT" in *--instance*) ok "jool --help lists --instance" ;; *) bad "jool --help omits --instance" ;; esac

run_capture "$BIN/jool_siit" --help
[ "$RC" -eq 0 ] && ok "jool_siit --help exits successfully" || bad "jool_siit --help exit=$RC"
case "$OUT" in *Usage*) ok "jool_siit --help prints usage" ;; *) bad "jool_siit --help has no usage" ;; esac

run_capture "$BIN/joold"
[ "$RC" -eq 22 ] && ok "joold no-argument path returns EINVAL (22)" || bad "joold no-argument exit=$RC"
case "$OUT" in *"Not enough arguments"*) ok "joold reports missing required arguments" ;; *) bad "joold missing-argument message absent" ;; esac

if [ "$TARGET" = "ohos" ]; then
    # HarmonyOS PC has no Jool kernel module. Exercise the real generic-netlink
    # command path and verify graceful absence handling without requiring root.
    for binary in jool jool_siit; do
        run_capture "$BIN/$binary" instance display
        if [ "$RC" -ne 0 ] && [ "$RC" -ne 139 ] && [ "$RC" -ne 134 ]; then
            ok "$binary netlink query fails closed without crashing (rc=$RC)"
        else
            bad "$binary netlink query returned unexpected rc=$RC"
        fi
        case "$OUT" in
            *"Jool's socket family doesn't seem to exist"*|*"Could not open the socket to kernelspace"*)
                ok "$binary reports unavailable kernel netlink family" ;;
            *) bad "$binary netlink failure lacks actionable message: $OUT" ;;
        esac
        case "$OUT" in *"Segmentation fault"*) bad "$binary netlink query segfaulted" ;; *) ok "$binary netlink query has no segmentation fault" ;; esac
    done
fi

echo "TEST_RESULT: PASS=$PASS FAIL=$FAIL TOTAL=$((PASS + FAIL))"
[ "$FAIL" -eq 0 ]
