#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the olsrd daemon executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

OLSRD="$(command -v olsrd)"
if [ -z "${OLSRD}" ]; then
    echo "FAIL: olsrd not found on PATH"
    exit 1
fi
echo "[test] found olsrd at ${OLSRD}"

TMPD="${TMPDIR:-/storage/Users/currentUser/tmp}"
OUT="${TMPD}/olsrd-test.$$.out"

# olsrd -h prints the version banner + usage, then olsr_exit() raises SIGTERM
# to itself and terminates quickly (expected exit status 143).  Guard with a
# background pid + safety kill in case it lingers on a platform quirk.
"${OLSRD}" -h >"${OUT}" 2>&1 &
PID=$!
sleep 8
if kill -0 "${PID}" 2>/dev/null; then
    echo "[test] olsrd still alive after 8s, killing"
    kill -9 "${PID}" 2>/dev/null || true
fi
wait "${PID}" 2>/dev/null || true

if ! grep -q "0.9.8" "${OUT}"; then
    echo "FAIL: version banner missing"
    cat "${OUT}"
    rm -f "${OUT}"
    exit 1
fi
echo "OK: version banner contains 0.9.8"

if ! grep -qi "usage: olsrd" "${OUT}"; then
    echo "FAIL: usage text missing"
    cat "${OUT}"
    rm -f "${OUT}"
    exit 1
fi
echo "OK: usage text present"

rm -f "${OUT}"
echo "[test] olsrd smoke test passed"
