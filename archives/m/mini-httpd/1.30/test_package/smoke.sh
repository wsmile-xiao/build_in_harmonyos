#!/bin/sh
# Consumer smoke test for mini-httpd 1.30: exercise both packaged binaries
# (htpasswd file creation + real HTTP round-trip against the server).
# Usage: smoke.sh <package_bindir>
# Kept POSIX-simple: the device /bin/sh is busybox ash (no $()+heredoc).
BINDIR="$1"

if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/mini_httpd" ] || [ ! -x "$BINDIR/htpasswd" ]; then
    echo "smoke: missing packaged binaries under $BINDIR" >&2
    exit 1
fi

# Scratch dir (mktemp) so no test artifacts leak into the package tree.
mkdir -p "$HOME/tmp"
WORK="$(mktemp -d "$HOME/tmp/minihttpd-smoke.XXXXXX")" || exit 1
trap 'rm -rf "$WORK"' EXIT
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1) htpasswd: create a credential file and check its shape.  ACME htpasswd
# 1.30 has no -b (batch) flag; it reads the password from stdin when stdin
# is not a tty (add_password fgets branch), which is what we use here.
HTPASSWD_RC=1
attempt=1
while [ $attempt -le 3 ]; do
    echo "wonderland" | "$BINDIR/htpasswd" -c "$WORK/htpasswd.out" alice > /dev/null 2>&1
    HTPASSWD_RC=$?
    if [ $HTPASSWD_RC -eq 0 ]; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done
if [ $HTPASSWD_RC -ne 0 ]; then
    echo "smoke: htpasswd -c failed rc=$HTPASSWD_RC" >&2
    exit 1
fi
if ! grep -q "^alice:" "$WORK/htpasswd.out"; then
    echo "smoke: htpasswd output malformed" >&2
    exit 1
fi

# 2) mini_httpd: serve a docroot on loopback, fetch it back, terminate.
rm -rf "$WORK/docroot"
mkdir -p "$WORK/docroot"
echo "hello from mini-httpd" > "$WORK/docroot/index.html"

PORT=18099
"$BINDIR/mini_httpd" -p $PORT -d "$WORK/docroot" -i "$WORK/mh.pid" > "$WORK/mh.log" 2>&1 &

RESP=""
attempt=1
while [ $attempt -le 6 ]; do
    sleep 1
    RESP="$(python3 "$SCRIPT_DIR/http_check.py" $PORT 2>/dev/null)"
    if [ -n "$RESP" ]; then
        break
    fi
    attempt=$((attempt + 1))
done

if [ -f "$WORK/mh.pid" ]; then
    kill $(cat "$WORK/mh.pid") 2>/dev/null
fi

if [ -z "$RESP" ]; then
    echo "smoke: no HTTP response (server log head: $(head -3 "$WORK/mh.log" 2>/dev/null))" >&2
    exit 1
fi
echo "$RESP" | grep -q "200" || { echo "smoke: HTTP status not 200" >&2; exit 1; }
echo "$RESP" | grep -q "mini_httpd/1.30" || { echo "smoke: Server header missing" >&2; exit 1; }
echo "$RESP" | grep -q "hello from mini-httpd" || { echo "smoke: body mismatch" >&2; exit 1; }

echo "mini-httpd consumer OK: htpasswd + HTTP round-trip"
exit 0
