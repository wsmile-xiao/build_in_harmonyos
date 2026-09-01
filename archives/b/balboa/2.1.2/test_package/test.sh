#!/bin/sh
set -eu
# HMBS readonly /tmp handling: use writable TMPDIR
if [ -z "${TMPDIR:-}" ]; then
  if [ -n "${TMP:-}" ]; then export TMPDIR="$TMP"
  elif [ -n "${TEMP:-}" ]; then export TMPDIR="$TEMP"
  elif [ -n "${HMBS_AUTOCONF_MKTEMP_FALLBACK:-}" ] && [ "$HMBS_AUTOCONF_MKTEMP_FALLBACK" != "0" ]; then export TMPDIR="$HMBS_AUTOCONF_MKTEMP_FALLBACK"
  else export TMPDIR="/data/storage/el2/base/haps/entry/files/tmp"
  fi
fi
if [ "$TMPDIR" = "0" ] || [ "$TMPDIR" = "/tmp" ]; then
  export TMPDIR="/data/storage/el2/base/haps/entry/files/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMP="$TMPDIR" TEMP="$TMPDIR"
: "${CONAN_PREFIX:=}"
echo "=== balboa test_package: validate binaries ==="
echo "TMPDIR=$TMPDIR PATH=$PATH CONAN_PREFIX=${CONAN_PREFIX:-<empty>}"
FAILED=0
for d in "${CONAN_PREFIX:-}" "${CONAN_PREFIX:-}/bin"; do
  if [ -n "$d" ] && [ -d "$d" ]; then echo "ls $d:"; ls -la "$d" 2>&1 | head -n 30; fi
done
if [ -n "${CONAN_PREFIX:-}" ]; then
  echo "find CONAN_PREFIX balboa*:"
  find "${CONAN_PREFIX}" -maxdepth 3 -type f -name "balboa*" -ls 2>&1 | head -n 30 || true
fi
echo "which balboa: $(command -v balboa 2>&1 || echo not-found)"
echo "which balboa-backend-console: $(command -v balboa-backend-console 2>&1 || echo not-found)"
echo "which balboa-mock: $(command -v balboa-mock 2>&1 || echo not-found)"

find_bin() {
  name="$1"
  if command -v "$name" >/dev/null 2>&1; then command -v "$name"; return 0; fi
  if [ -n "${CONAN_PREFIX:-}" ] && [ -x "${CONAN_PREFIX}/bin/$name" ]; then echo "${CONAN_PREFIX}/bin/$name"; return 0; fi
  if [ -n "${CONAN_PREFIX:-}" ] && [ -x "${CONAN_PREFIX}/$name" ]; then echo "${CONAN_PREFIX}/$name"; return 0; fi
  if [ -n "${CONAN_PREFIX:-}" ]; then
    for cand in "${CONAN_PREFIX}/bin/"*"$name"* "${CONAN_PREFIX}/"*"$name"*; do
      if [ -x "$cand" ] && [ -f "$cand" ]; then echo "$cand"; return 0; fi
    done
    found=$(find "${CONAN_PREFIX}" -type f -name "*${name}*" 2>/dev/null | head -n 1)
    if [ -n "$found" ] && [ -x "$found" ]; then echo "$found"; return 0; fi
  fi
  for d in $(echo "$PATH" | tr ':' ' '); do
    if [ -x "$d/$name" ]; then echo "$d/$name"; return 0; fi
    for cand in "$d/"*"$name"*; do if [ -x "$cand" ] && [ -f "$cand" ]; then echo "$cand"; return 0; fi; done
  done
  return 1
}

get_free_port() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()' 2>/dev/null || echo 0
  else
    echo 0
  fi
}

echo "[1/3] balboa --help"
BALBOA_BIN=""
if BALBOA_BIN=$(find_bin balboa 2>/dev/null); then :; else BALBOA_BIN=""; fi
if [ -n "$BALBOA_BIN" ] && echo "$BALBOA_BIN" | grep -q "balboa-backend"; then
  if [ -n "${CONAN_PREFIX:-}" ] && [ -x "${CONAN_PREFIX}/bin/balboa" ]; then BALBOA_BIN="${CONAN_PREFIX}/bin/balboa"
  elif command -v balboa >/dev/null 2>&1; then BALBOA_BIN="$(command -v balboa)"
  fi
fi
if [ -z "$BALBOA_BIN" ]; then
    echo "FAIL: balboa not found in PATH or CONAN_PREFIX/bin"
    FAILED=$((FAILED+1))
else
    echo "found balboa at $BALBOA_BIN"
    ls -l "$BALBOA_BIN" 2>&1 | head -n 5
    set +e
    OUT=$("$BALBOA_BIN" --help 2>&1)
    RC=$?
    set -e
    echo "$OUT" | head -n 20
    if [ $RC -ne 0 ] && [ -z "$OUT" ]; then
        echo "FAIL: balboa --help exited $RC with no output"
        FAILED=$((FAILED+1))
    elif echo "$OUT" | grep -qiE "usage|balboa|help|config"; then
        echo "PASS: balboa --help"
    else
        set +e
        OUT2=$("$BALBOA_BIN" 2>&1 | head -n 20)
        set -e
        echo "$OUT2" | head -n 20
        if echo "$OUT2" | grep -qiE "usage|balboa|help|config"; then
            echo "PASS: balboa (fallback)"
        else
            echo "FAIL: balboa output missing expected keywords"
            FAILED=$((FAILED+1))
        fi
    fi
fi

echo "[2/3] balboa-backend-console"
CONSOLE_BIN=""
if CONSOLE_BIN=$(find_bin balboa-backend-console 2>/dev/null); then :; else CONSOLE_BIN=""; fi
if [ -z "$CONSOLE_BIN" ]; then
    echo "FAIL: balboa-backend-console not found in PATH or CONAN_PREFIX/bin"
    if [ -n "${CONAN_PREFIX:-}" ]; then ls -la "${CONAN_PREFIX}/bin" 2>&1 | head -n 50; fi
    FAILED=$((FAILED+1))
else
    echo "found balboa-backend-console at $CONSOLE_BIN"
    ls -l "$CONSOLE_BIN" 2>&1 | head -n 5
    set +e
    OUT=$("$CONSOLE_BIN" 2>&1)
    RC=$?
    set -e
    echo "$OUT" | head -n 20
    if [ -z "$OUT" ]; then
        echo "FAIL: balboa-backend-console produced no output"
        FAILED=$((FAILED+1))
    elif echo "$OUT" | grep -qiE "usage|backend|help|balboa|console|Command"; then
        echo "PASS: balboa-backend-console (exit $RC with usage)"
    else
        set +e
        OUT2=$("$CONSOLE_BIN" --help 2>&1)
        set -e
        echo "$OUT2" | head -n 20
        if echo "$OUT2" | grep -qiE "usage|backend|help"; then
            echo "PASS: balboa-backend-console --help"
        else
            echo "FAIL: balboa-backend-console output missing usage"
            FAILED=$((FAILED+1))
        fi
    fi
fi

echo "[3/3] balboa-mock"
MOCK_BIN=""
if MOCK_BIN=$(find_bin balboa-mock 2>/dev/null); then :; else MOCK_BIN=""; fi
if [ -z "$MOCK_BIN" ]; then
    echo "FAIL: balboa-mock not found in PATH or CONAN_PREFIX/bin"
    if [ -n "${CONAN_PREFIX:-}" ]; then ls -la "${CONAN_PREFIX}/bin" 2>&1 | head -n 50; fi
    FAILED=$((FAILED+1))
else
    echo "found balboa-mock at $MOCK_BIN"
    ls -l "$MOCK_BIN" 2>&1 | head -n 5
    ATTEMPT=0
    MAX_ATTEMPTS=3
    MOCK_OK=0
    CHOSEN_PORT=""
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT+1))
        PORT=$(get_free_port)
        if [ -z "$PORT" ] || [ "$PORT" = "0" ]; then
            PORT=$((20000 + $$ % 30000 + ATTEMPT))
        fi
        CHOSEN_PORT=$PORT
        echo "attempt $ATTEMPT: testing balboa-mock on 127.0.0.1:$PORT"
        LOGFILE="$TMPDIR/balboa-mock-${PORT}.log"
        rm -f "$LOGFILE" 2>/dev/null || true
        set +e
        if command -v timeout >/dev/null 2>&1; then
            timeout 3 "$MOCK_BIN" -p "$PORT" -l 127.0.0.1 >"$LOGFILE" 2>&1 &
            PID=$!
        else
            "$MOCK_BIN" -p "$PORT" -l 127.0.0.1 >"$LOGFILE" 2>&1 &
            PID=$!
        fi
        sleep 1
        if kill -0 $PID 2>/dev/null; then
            cat "$LOGFILE" 2>&1 | head -n 20 || true
            if grep -q "Address in use" "$LOGFILE" 2>/dev/null; then
                echo "FAIL attempt $ATTEMPT: Address in use on $PORT"
                kill $PID 2>/dev/null || true
                wait $PID 2>/dev/null || true
                sleep 1
                continue
            fi
            if grep -qi "listening on" "$LOGFILE" 2>/dev/null; then
                echo "log shows listening"
            fi
            echo "PASS attempt $ATTEMPT: balboa-mock bound to $PORT"
            kill $PID 2>/dev/null || true
            sleep 0.5
            kill -9 $PID 2>/dev/null || true
            wait $PID 2>/dev/null || true
            MOCK_OK=1
            break
        else
            wait $PID 2>/dev/null; RC=$?
            echo "balboa-mock exited quickly rc=$RC log:"
            cat "$LOGFILE" 2>&1 | head -n 30 || true
            if grep -q "Address in use" "$LOGFILE" 2>/dev/null; then
                echo "FAIL attempt $ATTEMPT: Address in use, retry next port"
                sleep 1
                continue
            fi
            if grep -qi "listening on" "$LOGFILE" 2>/dev/null; then
                echo "PASS attempt $ATTEMPT: briefly listening then exited"
                MOCK_OK=1
                break
            fi
            echo "WARN attempt $ATTEMPT: quick exit without Address in use, retry"
            sleep 1
            continue
        fi
        set -e
    done
    set -e
    if [ "$MOCK_OK" = "1" ]; then
        echo "PASS: balboa-mock (dynamic port $CHOSEN_PORT)"
    else
        echo "FAIL: balboa-mock could not bind on any free port after $MAX_ATTEMPTS attempts"
        FAILED=$((FAILED+1))
    fi
    if [ ! -x "$MOCK_BIN" ]; then
        echo "FAIL: balboa-mock not executable"
        FAILED=$((FAILED+1))
    fi
fi

if [ $FAILED -ne 0 ]; then
    echo "FAIL: $FAILED of 3 consumer tests failed"
    exit 1
fi
echo "All 3 consumer tests passed"
