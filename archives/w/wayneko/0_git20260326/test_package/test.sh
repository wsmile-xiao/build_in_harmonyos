#!/data/service/hnp/bin/bash
# test_package/test.sh — layer-2 consumer test for wayneko.
#
# Executes the INSTALLED wayneko binary (resolved through the conanrun PATH)
# and asserts on real behaviour: exit codes and the exact diagnostic strings
# the program emits. This proves the shipped binary is genuinely exercised
# (R34 / CI L1e: removing bin/ makes this script fail).
#
# Upstream wayneko has no test suite; every assertion here is written by the
# port (see test_package/MANIFEST.yml).

pass=0
fail=0

ok()   { printf '        [ok]   %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '        [fail] %s\n' "$1"; fail=$((fail + 1)); }

# check_contains <label> <haystack> <needle>
check_contains() {
    case "$2" in
        *"$3"*) ok "$1" ;;
        *)      bad "$1 (missing: $3)" ;;
    esac
}

# check_eq <label> <actual> <expected>
check_eq() {
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi
}

echo "[test] wayneko binary: $(command -v wayneko)"

# ── 1. --help exits 0 and documents every flag ──────────────────────────
OUT="$(wayneko --help 2>&1)"; RC=$?
check_eq "--help exits 0" "$RC" "0"
check_contains "--help prints usage banner" "$OUT" "Usage: wayneko"
for flag in --background-colour --outline-colour --type --idle-sleep \
            --sleepiness --sleepiness-night --layer --follow-pointer \
            --survive-close; do
    check_contains "--help documents $flag" "$OUT" "$flag"
done

# ── 2. unknown flag is rejected ─────────────────────────────────────────
OUT="$(wayneko --no-such-flag 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "unknown flag exits non-zero ($RC)" \
                || bad "unknown flag should fail but exited 0"
check_contains "unknown flag reports 'Unknown option'" "$OUT" "Unknown option"

# ── 3. --type bogus is rejected ─────────────────────────────────────────
OUT="$(wayneko --type bogus 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "--type bogus exits non-zero ($RC)" \
                || bad "--type bogus should fail but exited 0"
check_contains "--type bogus error text" "$OUT" "Unknown argument 'bogus' for flag '--type'"

# ── 4. a flag without its parameter is rejected ─────────────────────────
OUT="$(wayneko --type 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "missing parameter exits non-zero ($RC)" \
                || bad "missing parameter should fail but exited 0"
check_contains "missing parameter error text" "$OUT" "requires a parameter"

# ── 5. malformed colour is rejected ─────────────────────────────────────
OUT="$(wayneko --background-colour nothex 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "malformed colour exits non-zero ($RC)" \
                || bad "malformed colour should fail but exited 0"
check_contains "malformed colour error text" "$OUT" "Invalid colour"

# ── 6. WAYLAND_DISPLAY unset is reported ────────────────────────────────
OUT="$(unset WAYLAND_DISPLAY; wayneko 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "unset WAYLAND_DISPLAY exits non-zero ($RC)" \
                || bad "unset WAYLAND_DISPLAY should fail but exited 0"
check_contains "unset WAYLAND_DISPLAY error text" "$OUT" "WAYLAND_DISPLAY is not set"

# ── 7. non-existent display is reported (binary reaches the connect path) ─
OUT="$(WAYLAND_DISPLAY=nonexistent-display wayneko 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "bogus WAYLAND_DISPLAY exits non-zero ($RC)" \
                || bad "bogus WAYLAND_DISPLAY should fail but exited 0"
check_contains "bogus WAYLAND_DISPLAY error text" "$OUT" "Can not connect to wayland display"

# ── summary ─────────────────────────────────────────────────────────────
echo "[test] test_package assertions: ${pass} passed, ${fail} failed"
if [ "$fail" -ne 0 ]; then
    echo "[test] FAILED"
    exit 1
fi
echo "[test] test_package PASS"
exit 0
