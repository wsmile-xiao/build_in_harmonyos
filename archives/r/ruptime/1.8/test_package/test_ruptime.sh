#!/usr/bin/env bash
# test_ruptime.sh — real smoke test for ruptime 1.8 (OHOS adaptation).
#
# Exercises the packaged scripts, not just their presence:
#   1. both scripts installed and executable
#   2. OHOS shebang (#!/usr/bin/env bash; /bin/bash does not exist on OHOS)
#   3. bash syntax check of both scripts
#   4. missing-config guard fails loudly instead of misbehaving
#   5. `ruptime -v` prints the version banner with a staged config
#      (upstream uses the `[ "${1}x" = "-vx" ]` idiom, so the flag is
#      single-letter `-v`; `-vx` would fall through to the nc query path)
#   6. `ruptimed` accepts a daemon-protocol line with staged config+spool
#
# Hermetic by design: needs only bash + coreutils. Config is staged under
# $TMPDIR via $RUPTIME_CONF_DIR (the recipe rewrites hardcoded /etc/ruptime
# to ${RUPTIME_CONF_DIR:-/etc/ruptime} because /etc is read-only on
# HarmonyOS PC). Paths that would need network/services (nc, xz, openssl,
# uptime) are never executed here.
set -euo pipefail

BIN_DIR="${1:?usage: test_ruptime.sh <package bin dir>}"
RUPTUME="$BIN_DIR/ruptime"
RUPTIMED="$BIN_DIR/ruptimed"

PASS=0
TOTAL=6

ok() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { echo "FAIL: $1"; }

# Hermetic staging dir: never touch /etc (read-only on OHOS devices).
CONF_BASE="$(mktemp -d)"
CONF_DIR="$CONF_BASE/ruptime"
mkdir -p "$CONF_DIR"
export RUPTIME_CONF_DIR="$CONF_DIR"
CONF="$CONF_DIR/ruptime.conf"
KEY="$CONF_DIR/ruptime.key"
SPOOL_BASE=""

cleanup() {
    rm -rf "$CONF_BASE"
    if [ -n "$SPOOL_BASE" ]; then
        rm -rf "$SPOOL_BASE"
    fi
}
trap cleanup EXIT

# 1. presence + executable bit
if [ -x "$RUPTUME" ] && [ -x "$RUPTIMED" ]; then
    ok "ruptime and ruptimed installed and executable"
else
    fail "ruptime/ruptimed missing or not executable in $BIN_DIR"
fi

# 2. OHOS shebang (recipe rewrites upstream #!/bin/bash)
if [ "$(head -n 1 "$RUPTUME")" = "#!/usr/bin/env bash" ] && \
   [ "$(head -n 1 "$RUPTIMED")" = "#!/usr/bin/env bash" ]; then
    ok "both scripts use #!/usr/bin/env bash"
else
    fail "unexpected shebang: $(head -n 1 "$RUPTUME") / $(head -n 1 "$RUPTIMED")"
fi

# 3. syntax check with the real interpreter
if bash -n "$RUPTUME" && bash -n "$RUPTIMED"; then
    ok "bash -n syntax check passed for both scripts"
else
    fail "bash syntax check failed"
fi

# 4. missing-config guard (empty $RUPTIME_CONF_DIR, nothing staged yet)
if [ -e "$CONF" ] || [ -e "$KEY" ]; then
    fail "staging dir unexpectedly non-empty: $CONF_DIR"
else
    if OUT="$("$RUPTUME" -v 2>&1)"; then
        fail "ruptime -v without config unexpectedly succeeded: $OUT"
    else
        case "$OUT" in
            *"NO CONFIG"*) ok "missing config fails loudly (guard works)" ;;
            *) fail "missing config gave unexpected output: $OUT" ;;
        esac
    fi
fi

# Stage a throwaway config + key (removed by the EXIT trap).
SPOOL_BASE="$(mktemp -d)"
mkdir -p "$SPOOL_BASE/spool"
printf '%s\n' "SERVER=localhost" "PORT=51300" "HOSTNAMECMD='hostname -f'" \
    "SPOOL=$SPOOL_BASE/spool" > "$CONF"
printf '%s' "conan-smoke-test-dummy-key" > "$KEY"

# 5. version banner with a valid config (single-letter -v; see header note).
if OUT="$("$RUPTUME" -v 2>&1)"; then
    case "$OUT" in
        *"version"*) ok "ruptime -v prints version banner: $OUT" ;;
        *) fail "ruptime -v output has no version banner: $OUT" ;;
    esac
else
    fail "ruptime -v with staged config exited nonzero: $OUT"
fi

# 6. daemon startup + protocol dispatch (unknown command => clean exit 0,
# exercises ruptimed config/key loading without needing nc or openssl)
if printf 'PROBE some-arg\n' | "$RUPTIMED" >/dev/null 2>&1; then
    ok "ruptimed accepts a protocol line and exits 0"
else
    fail "ruptimed protocol probe failed"
fi

echo "ruptime smoke test: $PASS/$TOTAL passed"
# HMBS machine evidence (deterministic PASS/TOTAL counters, not log grep).
if [ "$PASS" -eq "$TOTAL" ]; then TP_PASSED=true; else TP_PASSED=false; fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":${TP_PASSED},\"command\":\"bash test_ruptime.sh <package bin dir>\",\"discovered\":${TOTAL},\"passedCount\":${PASS}}"
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"shell","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"ruptime 1.8 upstream has no test suite (21-entry tag tarball, no test files or build system; see test_package/MANIFEST.yml audit)"}'
[ "$PASS" -eq "$TOTAL" ]
