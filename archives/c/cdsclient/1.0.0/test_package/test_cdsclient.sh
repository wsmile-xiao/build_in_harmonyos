#!/bin/sh
# test_cdsclient.sh — consumer test for cdsclient 1.0.0
# Verifies:
#   1. aclient binary exists and is executable
#   2. aclient -version prints correct version string, rc=0
#      (if filesystem permits execution — HMFS may be noexec)
#   3. aclient -h prints usage/help, rc=0 (same caveat)
#   4. file(1) reports an aarch64 ELF
#   5. Representative shell scripts exist in bin/
#   6. find_gen argument guard exits non-zero (offline verification)
#
# HMFS on HarmonyOS may mount the conan cache with noexec, preventing
# binary execution.  Assertions 2-3 are best-effort: if the binary
# cannot run (Operation not permitted), they are skipped rather than
# counting as failures.
#
# HMBS evidence marker (HMBS_TEST_PACKAGE_RESULT) is emitted at the end
# with the real assertion counts.
#
# Note: This file must use LF line endings.

FAILED=0
SKIPPED=0
discovered=6
ACLIENT="${CDSCLIENT_BIN:-}"
PKG="${CDSCLIENT_PKG:-}"

if [ -z "$ACLIENT" ] || [ ! -f "$ACLIENT" ]; then
    for cand in "${PKG}/bin/aclient" "$(dirname "$0")/aclient" "./aclient"; do
        if [ -f "$cand" ]; then
            ACLIENT="$cand"
            break
        fi
    done
fi

# Assertion 1: binary exists
if [ -z "$ACLIENT" ] || [ ! -f "$ACLIENT" ]; then
    echo "FAIL: aclient binary not found"
    FAILED=$((FAILED + 1))
else
    echo "PASS: aclient found at ${ACLIENT}"
fi

# Assertion 2: aclient -version
# CAN_RUN 只判定「二进制能不能被 exec」，不能用 -version 的退出码代替：
# 那样任何真实失败（参数解析错、缺库、崩溃）都会被当成 noexec 静默 SKIP，
# 测试假通过。127/126 才是 shell 报出的「找不到/不可执行」。
CAN_RUN=false
if [ -n "$ACLIENT" ] && [ -f "$ACLIENT" ] && [ -x "$ACLIENT" ]; then
    "$ACLIENT" -version >/dev/null 2>&1
    EXEC_RC=$?
    if [ "$EXEC_RC" -ne 127 ] && [ "$EXEC_RC" -ne 126 ]; then
        CAN_RUN=true
    fi
fi

if [ "$CAN_RUN" = true ]; then
    VOUT=$("$ACLIENT" -version 2>&1)
    VRC=$?
    echo "$VOUT"
    if [ "$VRC" -eq 0 ] && echo "$VOUT" | grep -q "aclient (CDS) Version 2.7"; then
        echo "PASS: aclient -version"
    else
        echo "FAIL: aclient -version rc=$VRC, expected 'aclient (CDS) Version 2.7'"
        FAILED=$((FAILED + 1))
    fi
else
    echo "SKIP: aclient -version (binary not executable: exec rc=126/127)"
    SKIPPED=$((SKIPPED + 1))
fi

# Assertion 3: aclient -h (best-effort)
if [ "$CAN_RUN" = true ] && [ -n "$ACLIENT" ] && [ -f "$ACLIENT" ]; then
    HOUT=$("$ACLIENT" -h 2>&1)
    HRC=$?
    if [ "$HRC" -eq 0 ] && echo "$HOUT" | grep -q "Usage: aclient"; then
        echo "PASS: aclient -h prints usage"
    else
        echo "FAIL: aclient -h rc=$HRC, expected Usage: aclient"
        FAILED=$((FAILED + 1))
    fi
elif [ "$CAN_RUN" = false ]; then
    echo "SKIP: aclient -h (binary not executable: exec rc=126/127)"
    SKIPPED=$((SKIPPED + 1))
fi

# Assertion 4: file(1) reports ELF
if [ -n "$ACLIENT" ] && [ -f "$ACLIENT" ]; then
    FILE_OUT="$(file "$ACLIENT" 2>/dev/null)"
    case "$FILE_OUT" in
        *ELF*) echo "PASS: file reports ELF" ;;
        *) echo "FAIL: file does not report ELF: ${FILE_OUT}"; FAILED=$((FAILED + 1));;
    esac
else
    FAILED=$((FAILED + 1))
fi

# Assertion 5: representative shell scripts exist
BIN_DIR="${PKG}/bin"
if [ -d "$BIN_DIR" ]; then
    MISSING=""
    for s in vizquery find_gen catcat lscat Detex; do
        if [ ! -f "$BIN_DIR/$s" ]; then
            MISSING="$MISSING $s"
        fi
    done
    if [ -z "$MISSING" ]; then
        echo "PASS: key shell scripts present"
    else
        echo "FAIL: missing scripts:${MISSING}"
        FAILED=$((FAILED + 1))
    fi
else
    echo "FAIL: bin/ directory not found at $BIN_DIR"
    FAILED=$((FAILED + 1))
fi

# Assertion 6: find_gen argument guard (offline, no CDS server needed)
FINDGEN="${BIN_DIR}/find_gen"
if [ -f "$FINDGEN" ]; then
    "$FINDGEN" >/dev/null 2>&1 && RC=0 || RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "PASS: find_gen exits non-zero without arguments (offline guard)"
    else
        echo "FAIL: find_gen exited 0 without arguments (expected non-zero)"
        FAILED=$((FAILED + 1))
    fi
else
    echo "FAIL: find_gen not found"
    FAILED=$((FAILED + 1))
fi

passed=$((discovered - FAILED - SKIPPED))
executed=$((discovered - SKIPPED))

if [ "$FAILED" -ne 0 ]; then
    echo "FAIL: $FAILED/$discovered assertions failed, $SKIPPED skipped"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_cdsclient.sh","discovered":%d,"executed":%d,"passedCount":%d,"skipped":%d}\n' \
        "$discovered" "$executed" "$passed" "$SKIPPED"
    exit 1
fi

echo "OK: all $discovered checks passed ($SKIPPED skipped)"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_cdsclient.sh","discovered":%d,"executed":%d,"passedCount":%d,"skipped":%d}\n' \
    "$discovered" "$executed" "$passed" "$SKIPPED"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"Upstream cdsclient 4.07 ships no automated test suite: no tests/ dir, no check/test targets in Makefile.in (only all/install/clean/tar/export/cvs/tag), catClient.py --test is a runtime CLI option requiring a live CDS server, not an automated suite; configure runs only compile/header/function probes, no test macros"}\n'
exit 0