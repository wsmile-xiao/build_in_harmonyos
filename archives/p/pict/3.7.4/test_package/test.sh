#!/bin/bash
# test_package/test.sh -- PICT 3.7.4 package verification
# Verifies the packaged `pict` binary exists and is a valid aarch64 ELF, and
# (when executable) actually generates pairwise test cases.
#
# SKIP policy (project rule R9/R34): SKIP is allowed ONLY when the failure is
# provably "cannot execute on this host" (exec/loader error, e.g. unsigned
# aarch64 ELF on an x86_64 build host, rc=126/127 or loader error in stderr).
# Any other real execution failure (rc != 0 while the binary ran) is a hard
# FAIL -- a genuine regression must never be masked as SKIP.
set -euo pipefail

PATH_DIRS=$(echo "${PATH}" | tr ':' '\n')
PKG_BIN=""
for d in ${PATH_DIRS}; do
    [ -n "${d}" ] || continue
    if [ -f "${d}/pict" ]; then PKG_BIN="${d}"; break; fi
done
echo "[test] package bin dir: ${PKG_BIN}"

if [ -z "${PKG_BIN}" ]; then
    echo "FAIL: pict not found on conanrun PATH"
    exit 1
fi

# is_aarch64_elf: 0x7f 'E' 'L' 'F' + e_machine==183 (0xB7, aarch64) at offset 18.
is_aarch64_elf() {
    local f="$1"
    [ -f "$f" ] || return 1
    local magic mach
    magic=$(dd if="$f" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$magic" = "7f454c46" ] || return 1
    mach=$(dd if="$f" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$mach" = "b700" ]
}

# cannot_exec: distinguish "binary cannot be loaded on this host" (SKIP-able)
# from a real run failure (must FAIL). Exec/loader failures surface as rc
# 126/127 or an exec-format/loader message on stderr.
cannot_exec() {
    local rc="$1" err="$2"
    [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ] && return 0
    if printf '%s\n' "$err" | grep -qiE 'exec format error|cannot execute binary|not a dynamic executable|no such file or directory|cannot open shared object|loader'; then
        return 0
    fi
    return 1
}

SMOKE_RC=0
SMOKE_OUT=""
run_smoke() {
    # returns 0 on success; on failure leaves SMOKE_RC/SMOKE_OUT for the caller.
    local model rc out nlines
    model=$(mktemp)
    cat > "${model}" <<'MODEL'
Type: Single, Span, Stripe
Size: 10, 100, 1000
Format: Quick, Slow
MODEL
    set +e
    out=$("${EXE}" "${model}" 2>&1); rc=$?
    set -e
    rm -f "${model}"
    SMOKE_RC=$rc
    SMOKE_OUT=$out
    if [ "${rc}" -ne 0 ]; then
        return "${rc}"
    fi
    # PICT output: header + generated rows, tab-separated. Success means at
    # least one non-empty line of generated cases.
    nlines=$(printf '%s\n' "${out}" | grep -cE '[^[:space:]]' || true)
    [ "${nlines}" -ge 1 ]
}

EXE="${PKG_BIN}/pict"
if [ ! -f "${EXE}" ]; then
    echo "FAIL: ${EXE} missing"; exit 1
fi

OK_COUNT=0
SKIP_COUNT=0
if [ -x "${EXE}" ]; then
    if run_smoke; then
        echo "OK: pict generated pairwise test cases (rc=0)"
        OK_COUNT=$((OK_COUNT + 1))
    else
        if cannot_exec "${SMOKE_RC}" "${SMOKE_OUT}"; then
            if is_aarch64_elf "${EXE}"; then
                echo "SKIP: pict cannot execute on this host (rc=${SMOKE_RC}, unsigned ELF / no OHOS loader); valid aarch64 ELF"
                SKIP_COUNT=$((SKIP_COUNT + 1))
            else
                echo "FAIL: pict not executable here and not a valid aarch64 ELF"
                exit 1
            fi
        else
            echo "FAIL: pict executed but failed (rc=${SMOKE_RC}): ${SMOKE_OUT%%$'\n'*}"
            exit 1
        fi
    fi
else
    if is_aarch64_elf "${EXE}"; then
        echo "SKIP: pict not executable here (unsigned ELF / no OHOS loader); valid aarch64 ELF"
        SKIP_COUNT=$((SKIP_COUNT + 1))
    else
        echo "FAIL: pict present but not a valid aarch64 ELF"
        exit 1
    fi
fi

echo "pict smoke tests completed: ${OK_COUNT} verified, ${SKIP_COUNT} skipped (unsigned-ELF platform limit)"
# SKIP 仅在"确证无法执行"(本宿主无法加载 aarch64)时产生，属平台限制可过
# （同 net-tools 先例）；真实运行失败已在上文作为 FAIL 拦截。
if [ "${OK_COUNT}" -gt 0 ] || [ "${SKIP_COUNT}" -gt 0 ]; then
    exit 0
fi
echo "FAIL: no verification outcome recorded"
exit 1
