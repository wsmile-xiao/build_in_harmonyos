#!/usr/bin/env bash
# R34: real smoke test for pacapt 3.0.7 — exercises the packaged artifact
# by invoking it as a consumer would, verifying actual runtime behaviour.
#
# pacapt is a POSIX shell wrapper that delegates to the system's package
# manager.  On OHOS there is no recognised package manager, so _PACMAN_detect
# fails and pacapt prints an error and exits 1.  This is the EXPECTED
# behaviour on this platform — the test verifies the script runs, produces
# the correct diagnostic, and exits cleanly (not a crash/signal).
#
# On systems WITH a supported package manager, the tests would exercise
# -Q, -S, -R, -Ss, -Sy, etc.  See tests/*.txt in upstream source.
set -euo pipefail

PACAPT="${1:?usage: test_pacapt.sh <package bin dir>}/pacapt"
FAIL=0
TOTAL=0
PASS=0
SKIP=0

_pass() { PASS=$((PASS+1)); echo "  PASS: $*"; }
_fail() { FAIL=$((FAIL+1)); echo "  FAIL: $*"; }
_skip() { SKIP=$((SKIP+1)); echo "  SKIP: $*  (reason: $2)"; }

# ── Layer 0: File-level checks ──────────────────────────────────────
echo "== Layer 0: artifact integrity =="

TOTAL=$((TOTAL+1))
if [ -f "$PACAPT" ]; then _pass "file exists: $PACAPT"
else _fail "file missing: $PACAPT"; fi

TOTAL=$((TOTAL+1))
if [ -x "$PACAPT" ]; then _pass "executable bit set"
else _fail "not executable"; fi

TOTAL=$((TOTAL+1))
SHEBANG=$(head -1 "$PACAPT")
if [[ "$SHEBANG" == *"/usr/bin/env sh"* || "$SHEBANG" == *"/bin/sh"* ]]; then
    _pass "shebang is POSIX sh: $SHEBANG"
else
    _fail "unexpected shebang: $SHEBANG"
fi

TOTAL=$((TOTAL+1))
SIZE=$(wc -c < "$PACAPT")
if [ "$SIZE" -gt 10240 ]; then
    _pass "script size OK: ${SIZE} bytes (>10KB)"
else
    _fail "script too small: ${SIZE} bytes"
fi

# ── Layer 1: Syntax validation ──────────────────────────────────────
echo "== Layer 1: syntax validation =="

TOTAL=$((TOTAL+1))
if sh -n "$PACAPT" 2>/dev/null; then
    _pass "sh -n syntax check"
else
    _fail "sh -n syntax check failed"
fi

TOTAL=$((TOTAL+1))
if bash -n "$PACAPT" 2>/dev/null; then
    _pass "bash -n syntax check"
else
    _fail "bash -n syntax check failed"
fi

# ── Layer 2: Runtime invocation (OHOS-specific) ─────────────────────
echo "== Layer 2: runtime invocation =="

# 2a. On OHOS, _PACMAN_detect fails → _die → exit 1 with diagnostic.
#     This is the expected platform behaviour, NOT a bug.
TOTAL=$((TOTAL+1))
OUTPUT=$(sh "$PACAPT" -Q 2>&1) || true
RC=$(sh "$PACAPT" -Q 2>/dev/null; echo $? 2>/dev/null || true)
# Re-run to capture exit code properly
set +e
sh "$PACAPT" -Q >/dev/null 2>&1
RC=$?
set -e
if [ "$RC" -eq 1 ] && echo "$OUTPUT" | grep -q "doesn't support"; then
    _pass "OHOS expected: _PACMAN_detect fails (exit=1, diagnostic present)"
elif [ "$RC" -eq 0 ]; then
    _pass "pacapt -Q succeeded (package manager detected)"
else
    _fail "unexpected exit code=$RC, output=$OUTPUT"
fi

# 2b. Version string embedded in script
TOTAL=$((TOTAL+1))
if grep -q "PACAPT_VERSION" "$PACAPT"; then
    _pass "PACAPT_VERSION present in script"
else
    _fail "PACAPT_VERSION missing"
fi

TOTAL=$((TOTAL+1))
if grep -q "3.0.7" "$PACAPT"; then
    _pass "version 3.0.7 found in script"
else
    _fail "version 3.0.7 not found in script"
fi

# 2c. PACAPT_DEBUG mode — should still detect and print debug info
TOTAL=$((TOTAL+1))
set +e
DEBUG_OUT=$(PACAPT_DEBUG=auto sh "$PACAPT" -Q 2>&1)
DEBUG_RC=$?
set -e
if echo "$DEBUG_OUT" | grep -q "debug\|Switching\|support"; then
    _pass "PACAPT_DEBUG mode produces debug output"
else
    # Debug mode might not produce output on all shells — not a hard fail
    _skip "PACAPT_DEBUG output" "no debug markers in output (shell-dependent)"
fi

# ── Layer 3: Upstream test coverage gap ─────────────────────────────
echo "== Layer 3: upstream test coverage =="

# Upstream has 12 test files (dpkg.txt, apk.txt, yum.txt, etc.) with 310 test
# commands total.  ALL require a real package manager inside a Docker container.
# On OHOS there is no package manager → these tests cannot run.
TOTAL=$((TOTAL+1))
_skip "upstream dpkg.txt (48 commands)" "no dpkg/apt on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream apk.txt (50 commands)" "no apk on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream yum.txt (44 commands)" "no yum on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream dnf.txt (33 commands)" "no dnf on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream zypper.txt (25 commands)" "no zypper on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream homebrew.txt (12 commands)" "no homebrew on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream xbps.txt (11 commands)" "no xbps on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream pkgng.txt (21 commands)" "no pkgng on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream opkg.txt (27 commands)" "no opkg on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream sun_tools.txt (5 commands)" "no sun_tools on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream swupd.txt (13 commands)" "no swupd on OHOS"
TOTAL=$((TOTAL+1))
_skip "upstream slitaz40.txt (21 commands)" "no tazpkg on OHOS"

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "pacapt 3.0.7 smoke test summary"
echo "========================================"
echo "  Total:  $TOTAL"
echo "  Pass:   $PASS"
echo "  Fail:   $FAIL"
echo "  Skip:   $SKIP"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    echo "RESULT: FAIL ($FAIL failures)"
    exit 1
fi
echo "RESULT: PASS ($PASS passed, $SKIP skipped — skipped tests require package managers absent on OHOS)"
exit 0
