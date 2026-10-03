#!/usr/bin/env bash
# End-to-end consumer test for medusa 2.3 (L0d: complete consumer case).
#
# test_medusa.sh proves that the packaged binary starts and can dlopen() its
# service modules.  That is a real check, but it is still only assertions about
# the artifact: it never makes medusa do the job it exists for.  This test does:
#
#   1. a deterministic FTP server (python3, stdlib only) is started on
#      127.0.0.1 with exactly one valid credential pair;
#   2. the packaged `medusa' binary is run against it as a normal audit
#      (`-M ftp -h 127.0.0.1 -n PORT -u USER -p PASS -t 1 -T 1`);
#   3. the run is accepted only when
#        - the server really received the FTP dialogue (USER + PASS + auth ok),
#        - medusa reported `[ftp] Host: ... [SUCCESS]' for that credential,
#        - a wrong password was rejected in the negative control, and
#        - stdout/stderr contain no fatal error.
#
# Everything runs on loopback, so no external network is required.
#
# Usage: test_medusa_e2e.sh </path/to/medusa> [</path/to/modules>]
set -euo pipefail

BIN="${1:?usage: test_medusa_e2e.sh <path-to-medusa> [<module-dir>]}"
MODULE_DIR="${2:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_ROOT="$(cd "$(dirname "$BIN")/.." && pwd)"

E2E_USER="${MEDUSA_E2E_USER:-e2euser}"
E2E_PASS="${MEDUSA_E2E_PASS:-e2epass}"
E2E_BAD_PASS="${MEDUSA_E2E_BAD_PASS:-wrongpass}"
E2E_MODULE="${MEDUSA_E2E_MODULE:-ftp}"

if [ ! -x "$BIN" ] && [ ! -f "$BIN" ]; then
  echo "[fail] medusa binary not found: $BIN" >&2
  exit 1
fi
if [ ! -f "$HERE/ftp_e2e_server.py" ]; then
  echo "[fail] ftp_e2e_server.py missing next to $HERE" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
      PYTHON_BIN="$cand"
      break
    fi
  done
fi
# The CI worker's PATH is minimal (/data/app/bin, /system/bin, ...) and does not
# include the user or HNP tool dirs, so fall back to the well-known OHOS
# locations before giving up.
if [ -z "$PYTHON_BIN" ]; then
  for cand in "${HOME:-/storage/Users/currentUser}/usr/local/bin/python3" \
              /data/service/hnp/bin/python3 \
              /usr/local/bin/python3 \
              /usr/bin/python3; do
    if [ -x "$cand" ]; then
      PYTHON_BIN="$cand"
      break
    fi
  done
fi
if [ -z "$PYTHON_BIN" ]; then
  echo "[fail] no python3/python found (PATH and the usual OHOS locations);" >&2
  echo "       the e2e FTP server needs it (set PYTHON_BIN to override)" >&2
  exit 1
fi

# OHOS has no writable /tmp: honour TMPDIR and fail loudly instead of falling
# back to a path that cannot be written.
: "${TMPDIR:=${HOME:-/tmp}/tmp}"
mkdir -p "$TMPDIR" 2>/dev/null || true

# medusa aborts with `FATAL: Error loading OpenSSL 'legacy' provider.' unless
# OPENSSL_MODULES points at a directory holding legacy.so; the package ships its
# own copy (see the recipe's package()).  test_medusa.sh sets this too, but this
# script is also useful stand-alone, so repeat the same resolution.
PROVIDER_DIR=""
if [ -n "${OPENSSL_MODULES:-}" ] && [ -f "${OPENSSL_MODULES}/legacy.so" ]; then
  PROVIDER_DIR="$OPENSSL_MODULES"
else
  : "${CONAN_HOME:=$HOME/.conan2}"
  for cand in "$PKG_ROOT/lib/ossl-modules" \
              $CONAN_HOME/p/opens*/p/lib/ossl-modules \
              $CONAN_HOME/p/*/p/lib/ossl-modules; do
    if [ -f "$cand/legacy.so" ]; then
      PROVIDER_DIR="$cand"
      break
    fi
  done
fi
if [ -z "$PROVIDER_DIR" ]; then
  echo "[fail] OpenSSL 'legacy' provider not found" >&2
  echo "[hint] export OPENSSL_MODULES=<dir containing legacy.so>" >&2
  exit 1
fi
export OPENSSL_MODULES="$PROVIDER_DIR"

E2E_DIR="$(mktemp -d "${TMPDIR%/}/medusa-e2e.XXXXXX")" || {
  echo "[fail] cannot create a working directory in TMPDIR=$TMPDIR" >&2
  exit 1
}
SRV_LOG="$E2E_DIR/server.log"
OUT_OK="$E2E_DIR/audit-ok.log"
OUT_BAD="$E2E_DIR/audit-bad.log"
SRV_PID=""

cleanup() {
  if [ -n "$SRV_PID" ] && kill -0 "$SRV_PID" 2>/dev/null; then
    kill "$SRV_PID" 2>/dev/null || true
    wait "$SRV_PID" 2>/dev/null || true
  fi
  rm -rf "$E2E_DIR"
}
trap cleanup EXIT

if [ -z "${MEDUSA_MODULE_PATH:-}" ]; then
  if [ -n "$MODULE_DIR" ]; then
    export MEDUSA_MODULE_PATH="$MODULE_DIR"
  elif [ -d "$PKG_ROOT/lib/medusa/modules" ]; then
    export MEDUSA_MODULE_PATH="$PKG_ROOT/lib/medusa/modules"
  fi
fi
if [ -z "${MEDUSA_MODULE_PATH:-}" ] || [ ! -d "$MEDUSA_MODULE_PATH" ]; then
  echo "[fail] medusa module directory not found (MEDUSA_MODULE_PATH=${MEDUSA_MODULE_PATH:-<unset>})" >&2
  exit 1
fi

echo "== medusa end-to-end consumer test =="
echo "binary      : $BIN"
echo "module dir  : ${MEDUSA_MODULE_PATH:-<unset>}"
echo "python      : $PYTHON_BIN ($($PYTHON_BIN -V 2>&1))"
echo "work dir    : $E2E_DIR"

start_server() {
  rm -f "$SRV_LOG"
  "$PYTHON_BIN" -u "$HERE/ftp_e2e_server.py" \
    --host 127.0.0.1 --port 0 \
    --user "$E2E_USER" --pass "$E2E_PASS" \
    --rounds 0 --timeout 30 \
    >"$SRV_LOG" 2>&1 &
  SRV_PID=$!
}

wait_for_port() {
  # Poll the server log for FTPD_READY; the port is chosen by the OS.
  local i=0 port=""
  while [ "$i" -lt 100 ]; do
    port="$(sed -n 's/^FTPD_READY .*port=\([0-9][0-9]*\).*$/\1/p' "$SRV_LOG" 2>/dev/null | head -n 1)"
    if [ -n "$port" ]; then
      echo "$port"
      return 0
    fi
    if ! kill -0 "$SRV_PID" 2>/dev/null; then
      echo "[fail] FTP e2e server exited during startup:" >&2
      cat "$SRV_LOG" >&2 || true
      return 1
    fi
    i=$((i + 1))
    sleep 0.1
  done
  echo "[fail] FTP e2e server did not report FTPD_READY within 10s:" >&2
  cat "$SRV_LOG" >&2 || true
  return 1
}

# medusa prefixes every line with "YYYY-MM-DD HH:MM:SS ACCOUNT FOUND: " whenever
# stdout is not a tty, so the pattern keeps the optional timestamp/label prefix
# while still requiring the module, host, user, password and [SUCCESS] marker.
success_pattern() {
  # $1 = password
  printf '^(.* )?\\[%s\\] Host: 127\\.0\\.0\\.1 User: %s Password: %s \\[SUCCESS\\]' \
    "$E2E_MODULE" "$E2E_USER" "$1"
}

run_medusa() {
  # $1 = password, $2 = output file
  set +e
  "$BIN" -M "$E2E_MODULE" -h 127.0.0.1 -n "$E2E_PORT" \
    -u "$E2E_USER" -p "$1" -t 1 -T 1 -g 5 -r 1 -R 0 -v 5 \
    >"$2" 2>&1
  local rc=$?
  set -e
  return "$rc"
}

# ---------------------------------------------------------------- positive run
start_server
E2E_PORT="$(wait_for_port)"
echo "[info] FTP e2e server listening on 127.0.0.1:$E2E_PORT (pid $SRV_PID)"

run_medusa "$E2E_PASS" "$OUT_OK" || true
echo "---- medusa output (valid credential) ----"
cat "$OUT_OK"
echo "------------------------------------------"

if grep -q "Error loading OpenSSL" "$OUT_OK"; then
  echo "[fail] medusa could not load its OpenSSL providers" >&2
  exit 1
fi
if grep -qE 'failed: Server sent unknown or no response' "$OUT_OK"; then
  echo "[fail] medusa could not talk to the FTP service:" >&2
  sed -n '1,40p' "$OUT_OK" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi

# Server side: the FTP dialogue must really have happened.
if ! grep -q "^E2E USER $E2E_USER\$" "$SRV_LOG"; then
  echo "[fail] the server never received 'USER $E2E_USER'" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi
echo "[ok] server received the USER command"
if ! grep -q "^E2E PASS " "$SRV_LOG"; then
  echo "[fail] the server never received a PASS command" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi
echo "[ok] server received the PASS command"

# Give the server a moment to flush its AUTH_OK marker after medusa exits.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  grep -q "^E2E AUTH_OK" "$SRV_LOG" && break
  sleep 0.2
done
if ! grep -q "^E2E AUTH_OK" "$SRV_LOG"; then
  echo "[fail] the server never authenticated the credential pair" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi
echo "[ok] live FTP service authenticated the credential pair"

# Client side: medusa must report the find for that host/user/password.
if ! grep -qE "$(success_pattern "$E2E_PASS")" "$OUT_OK"; then
  echo "[fail] medusa did not report the expected SUCCESS line" >&2
  cat "$OUT_OK" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi
echo "[ok] medusa reported the audited credential as found"

# ------------------------------------------------------- negative control run
kill "$SRV_PID" 2>/dev/null || true
wait "$SRV_PID" 2>/dev/null || true
SRV_PID=""
start_server
E2E_PORT="$(wait_for_port)"
echo "[info] negative control on 127.0.0.1:$E2E_PORT"

run_medusa "$E2E_BAD_PASS" "$OUT_BAD" || true
echo "---- medusa output (wrong password) ----"
cat "$OUT_BAD"
echo "-----------------------------------------"

if grep -qE "$(success_pattern "$E2E_BAD_PASS")" "$OUT_BAD"; then
  echo "[fail] medusa reported SUCCESS for a credential the server rejected" >&2
  exit 1
fi
if grep -q "^E2E AUTH_OK" "$SRV_LOG"; then
  echo "[fail] the server authenticated a credential it should have rejected" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi
if ! grep -q "^E2E PASS $E2E_BAD_PASS\$" "$SRV_LOG"; then
  echo "[fail] the server never received the wrong password (dialogue did not run)" >&2
  cat "$SRV_LOG" >&2 || true
  exit 1
fi
echo "[ok] wrong password was transmitted and rejected; no false positive"

if grep -qE 'FATAL:|Error loading OpenSSL' "$OUT_OK" "$OUT_BAD"; then
  echo "[fail] a fatal error appeared in the audit output" >&2
  exit 1
fi
echo "[ok] no fatal errors in either run"

echo "ALL MEDUSA E2E TESTS PASSED"
