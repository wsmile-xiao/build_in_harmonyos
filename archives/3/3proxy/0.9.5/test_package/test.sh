#!/bin/sh
# test_package consumer test for 3proxy 0.9.5.
#  1) usage/version banner of the installed 3proxy binary
#  2) functional smoke: HTTP proxy listener on a non-privileged loop-back port
#     accepts a real TCP connection (capability probe for an unprivileged user)
export PATH="$PATH:/system/bin"

echo "--- 3proxy 0.9.5 consumer verification ---"

TPROXY="$(command -v 3proxy 2>/dev/null || true)"
if [ -z "$TPROXY" ] && [ -n "${CONAN_BIN_DIRS_3PROXY:-}" ]; then
  TPROXY="$CONAN_BIN_DIRS_3PROXY/3proxy"
fi
if [ -z "$TPROXY" ]; then
  echo "FAIL: 3proxy not found in PATH ($PATH)"
  exit 1
fi
echo "binary: $TPROXY"

PYBIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
if [ -z "$PYBIN" ]; then
  echo "FAIL: neither python3 nor python found in PATH"
  exit 1
fi

# --- check 1: usage banner carries the packaged version ---
OUT="$("$TPROXY" -h 2>&1)"
echo "$OUT" | grep -q "3proxy-0.9.5" || {
  echo "FAIL: unexpected -h output: [$OUT]"
  exit 1
}
BANNER="$(echo "$OUT" | grep "3proxy tiny proxy server")"
echo "PASS 1: usage banner -> $BANNER"

# --- check 2: non-privileged port bind + real TCP accept ---
PORT=$((18000 + ($$ % 900)))
CF="$PWD/tp-smoke.cfg"
printf 'auth none\nproxy -p%s -i127.0.0.1\n' "$PORT" > "$CF"
"$TPROXY" "$CF" &
PID=$!
OK=0
i=0
while [ "$i" -lt 15 ]; do
  if "$PYBIN" -c "import socket,sys
try:
    s=socket.create_connection(('127.0.0.1', $PORT), 1); s.close(); sys.exit(0)
except Exception:
    sys.exit(1)"; then
    OK=1
    break
  fi
  i=$((i + 1))
  sleep 1
done
kill "$PID" 2>/dev/null
wait "$PID" 2>/dev/null
rm -f "$CF"
if [ "$OK" != "1" ]; then
  echo "FAIL: no listener on 127.0.0.1:$PORT after ${i}s"
  exit 1
fi
echo "PASS 2: HTTP proxy accepted a TCP connection on 127.0.0.1:$PORT"

echo "test 3proxy 0.9.5: 2/2 checks PASS"
exit 0
