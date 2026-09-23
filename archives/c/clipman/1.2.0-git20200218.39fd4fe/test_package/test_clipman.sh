#!/data/service/hnp/bin/bash
# test_package harness — clipman 1.2.0-git20200218.39fd4fe
# Usage: test_clipman.sh
#   Runs in the conanrun env (PATH includes the installed bin/clipman).
#
# Drives the packaged binary the way a real consumer would, without any
# Wayland session or external selector:
#   1) clipman --version            -> output contains 1.2.0
#   2) store item A (-P)            -> temp histpath JSON contains A
#   3) store item B (-P)            -> temp histpath JSON contains A and B
#   4) pick --tool STDOUT           -> output contains A
#   5) pick --tool STDOUT           -> output contains B
#   6) clipman --help               -> exit code 0
# Each step prints one "PASS: ..." line. The script counts those lines
# and emits the HMBS_TEST_PACKAGE_RESULT evidence marker with
# discovered = the real assertion count (6) and passedCount = the number
# of PASS lines observed this run (bankstown-lv2 precedent).
#
# Notes:
# - store uses -P/--no-persist so no wl-copy is required on the device.
# - clear/restore are deliberately NOT covered: clear --all runs
#   `wl-copy -c` first and fails without wl-copy installed; restore only
#   serves to wl-copy. Both are unusable in a headless test env.
set -uo pipefail

# Real assertion count in this harness (matches MANIFEST.yml).
DISCOVERED=6

BIN="clipman"
if ! command -v "$BIN" >/dev/null 2>&1; then
    echo "FATAL: clipman not on PATH (conanrun env missing?)" >&2
    exit 2
fi

# Temp history file goes to a task-private writable dir (HMBS_TMPDIR /
# TMPDIR first), never into the test_package source tree.
TMPD=""
for cand in "${HMBS_TMPDIR:-}" "${TMPDIR:-}" "${TMP:-}" "/data/local/tmp"; do
    [ -n "${cand}" ] || continue
    if mkdir -p "${cand}" 2>/dev/null; then
        TMPD="${cand}"
        break
    fi
done
if [ -z "${TMPD}" ]; then
    echo "FATAL: no writable temp dir" >&2
    exit 2
fi
HIST="${TMPD}/clipman-test-hist-$$.json"
rm -f "${HIST}"

ITEM_A="hmbs-clipman-item-alpha"
ITEM_B="hmbs-clipman-item-beta"

run_checks() {
    FAILED=0

    # --- 1. --version ---
    VER_OUT="$("$BIN" --version 2>&1 || true)"
    echo "[test] clipman --version -> ${VER_OUT}"
    if printf '%s\n' "$VER_OUT" | grep -qF "1.2.0"; then
        echo "PASS: --version contains 1.2.0"
    else
        echo "FAIL: --version output missing 1.2.0" >&2
        FAILED=1
    fi

    # --- 2. store item A ---
    if printf '%s\n' "$ITEM_A" | "$BIN" store --histpath "$HIST" -P 2>"${TMPD}/store-a.err"; then
        if [ -f "$HIST" ] && grep -qF "$ITEM_A" "$HIST"; then
            echo "PASS: store persists item A to histpath JSON"
        else
            echo "FAIL: histpath JSON missing item A" >&2
            FAILED=1
        fi
    else
        echo "FAIL: store item A (rc!=0)" >&2
        cat "${TMPD}/store-a.err" >&2 || true
        FAILED=1
    fi
    rm -f "${TMPD}/store-a.err"

    # --- 3. store item B, history keeps both ---
    if printf '%s\n' "$ITEM_B" | "$BIN" store --histpath "$HIST" -P 2>"${TMPD}/store-b.err"; then
        if [ -f "$HIST" ] && grep -qF "$ITEM_A" "$HIST" && grep -qF "$ITEM_B" "$HIST"; then
            echo "PASS: store appends item B, history holds both items"
        else
            echo "FAIL: histpath JSON missing A/B after second store" >&2
            FAILED=1
        fi
    else
        echo "FAIL: store item B (rc!=0)" >&2
        cat "${TMPD}/store-b.err" >&2 || true
        FAILED=1
    fi
    rm -f "${TMPD}/store-b.err"

    # --- 4+5. pick --tool STDOUT shows both items ---
    PICK_OUT="$("$BIN" pick --tool STDOUT --histpath "$HIST" 2>"${TMPD}/pick.err" || true)"
    if printf '%s\n' "$PICK_OUT" | grep -qF "$ITEM_A"; then
        echo "PASS: pick STDOUT shows item A"
    else
        echo "FAIL: pick STDOUT missing item A" >&2
        cat "${TMPD}/pick.err" >&2 || true
        FAILED=1
    fi
    if printf '%s\n' "$PICK_OUT" | grep -qF "$ITEM_B"; then
        echo "PASS: pick STDOUT shows item B"
    else
        echo "FAIL: pick STDOUT missing item B" >&2
        cat "${TMPD}/pick.err" >&2 || true
        FAILED=1
    fi
    rm -f "${TMPD}/pick.err"

    # --- 6. --help exits 0 ---
    if "$BIN" --help >/dev/null 2>&1; then
        echo "PASS: --help exits 0"
    else
        echo "FAIL: --help non-zero exit" >&2
        FAILED=1
    fi

    rm -f "${HIST}"
    return "$FAILED"
}

RUN_OUT="$(run_checks 2>&1)"
RUN_RC=$?
printf '%s\n' "$RUN_OUT"

PASS_COUNT="$(printf '%s\n' "$RUN_OUT" | grep -c '^PASS: ' || true)"

if [ "$RUN_RC" -eq 0 ] && [ "$PASS_COUNT" -ge "$DISCOVERED" ]; then
    echo "[OK] clipman consumer behavioral test PASS (${PASS_COUNT}/${DISCOVERED})"
    FAILED=0
else
    echo "[FAIL] clipman consumer behavioral test rc=${RUN_RC}, passed=${PASS_COUNT}/${DISCOVERED}" >&2
    FAILED=1
fi

if [ "$FAILED" -eq 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test_clipman.sh <bin/clipman> (version+store+pick behavioral)","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASS_COUNT"
else
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test_clipman.sh <bin/clipman> (version+store+pick behavioral)","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASS_COUNT"
fi
exit "$FAILED"
