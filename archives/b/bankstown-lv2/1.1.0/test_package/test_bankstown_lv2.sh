#!/usr/bin/env bash
# test_package harness — bankstown-lv2 1.1.0
# Usage: test_bankstown_lv2.sh <path-to-bankstown.lv2-bundle>
#
# 1) Compiles test_package/src/test_bankstown_lv2.c (real LV2 C API consumer:
#    dlopen + lv2_descriptor + instantiate/connect_port/run/cleanup) with the
#    OHOS clang, linking libdl and libm.
# 2) Runs the compiled test binary against the packaged bundle; the C program
#    prints one "PASS: ..." line per verified step.
# 3) Counts those PASS lines and emits the HMBS_TEST_PACKAGE_RESULT evidence
#    marker with discovered = the real assertion count in the C consumer
#    (16) and passedCount = the number of PASS lines observed this run. This
#    is a real per-run count, not a fixed "all passed" constant — a binary
#    that fails early (e.g. dlopen) yields a lower passedCount and non-zero rc.
set -uo pipefail

BUNDLE="${1:?Usage: test_bankstown_lv2.sh <path-to-bankstown.lv2-bundle>}"
FAILED=0

# Real assertion count in the C consumer (matches MANIFEST.yml):
#   dlopen, dlsym lv2_descriptor, lv2_descriptor(0) non-null, URI non-null,
#   URI match, 6 function-pointer checks, instantiate non-null, 12-port
#   connect, run() wrote non-zero output, bypass passthrough, cleanup
#   = 16 steps, each printing "PASS: ...".
DISCOVERED=16

# --- locate the test source (alongside this script) ---
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_C="${HERE}/src/test_bankstown_lv2.c"
if [ ! -f "${SRC_C}" ]; then
    echo "FATAL: test source not found: ${SRC_C}" >&2
    exit 2
fi

CLANG="${CLANG:-}"
if [ -z "${CLANG}" ]; then
    for cand in /data/service/hnp/bin/clang clang /storage/Users/currentUser/usr/local/bin/clang; do
        if command -v "$cand" >/dev/null 2>&1; then CLANG="$cand"; break; fi
    done
fi
if [ -z "${CLANG}" ]; then
    echo "FATAL: no clang found" >&2
    exit 2
fi

# 编译产物写进任务独立的可写临时目录（HMBS_TMPDIR/TMPDIR），绝不写进
# test_package 源码目录——conan test_package 的 build_folder 就等于源码
# 目录，此前二进制落在这里被误提交进 git。按优先级取首个可写目录。
TMPD=""
for cand in "${HMBS_TMPDIR:-}" "${TMPDIR:-}" "${TMP:-}" "/data/local/tmp"; do
    [ -n "${cand}" ] || continue
    if mkdir -p "${cand}" 2>/dev/null; then
        TMPD="${cand}"
        break
    fi
done
if [ -z "${TMPD}" ]; then
    TMPD="${HERE}"
fi

BIN="${TMPD}/test_bankstown_lv2"
ERR="${TMPD}/test_bankstown_lv2_compile.err"
echo "[test] compiling consumer test with ${CLANG} (workdir ${TMPD})"
if "${CLANG}" -O1 -o "${BIN}" "${SRC_C}" -ldl -lm 2>"${ERR}"; then
    echo "[OK] compiled test_bankstown_lv2.c"
    rm -f "${ERR}"
else
    echo "[FAIL] compile test_bankstown_lv2.c" >&2
    cat "${ERR}" >&2
    rm -f "${BIN}" "${ERR}"
    FAILED=1
    # No assertions ran: discovered=16 (expected), passedCount=0 (honest).
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test_bankstown_lv2.sh <bundle>","discovered":%d,"passedCount":0}\n' "$DISCOVERED"
    exit 1
fi

echo "[test] running consumer test against ${BUNDLE}"
RUN_OUT="$("${BIN}" "${BUNDLE}" 2>&1)"
RUN_RC=$?
rm -f "${BIN}"   # 清理编译产物，避免污染源码目录/临时目录
printf '%s\n' "$RUN_OUT"

PASS_COUNT="$(printf '%s\n' "$RUN_OUT" | grep -c '^PASS: ' || true)"

if [ "${RUN_RC}" -eq 0 ] && [ "${PASS_COUNT}" -ge "${DISCOVERED}" ]; then
    echo "[OK] bankstown-lv2 LV2 C API consumer test PASS (${PASS_COUNT}/${DISCOVERED})"
    FAILED=0
else
    echo "[FAIL] bankstown-lv2 LV2 C API consumer test rc=${RUN_RC}, passed=${PASS_COUNT}/${DISCOVERED}" >&2
    FAILED=1
fi

if [ "${FAILED}" -eq 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test_bankstown_lv2.sh <bundle> (dlopen+LV2 C API lifecycle)","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASS_COUNT"
else
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test_bankstown_lv2.sh <bundle>","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASS_COUNT"
fi
exit "${FAILED}"