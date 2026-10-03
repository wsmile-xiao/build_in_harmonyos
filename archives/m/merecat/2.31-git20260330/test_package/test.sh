#!/bin/sh
# test_package/test.sh - consumer smoke test for the packaged merecat server.
#
# Usage: test.sh <absolute-work-dir>
# Everything is kept inside the given directory: /tmp is read-only on HarmonyOS
# PC, HMDFS forbids writing into freshly created mktemp directories (E114), and
# the bundled bash cannot resolve $PWD here (E386), so paths are passed in.
set -eu
# pipefail keeps "cmd | grep -q" failures visible where supported.
(set -o pipefail) 2>/dev/null && set -o pipefail || true

WORK="${1:?usage: test.sh <absolute-work-dir>}"
MERECAT="$(command -v merecat)"
echo "[test] merecat -V -> $("$MERECAT" -V)"

# Refuse to remove anything but an ordinary directory below the root: the
# caller passes a throw-away directory created for this run, and a bad value
# ("", "/", "/tmp", a relative path, ...) must never become a recursive
# removal.  PR review 192438012 (P3).
safe_rm_rf() {
    case "$1" in
        "" | / | . | .. | */. | */..)
            echo "[test] FAIL - refusing to remove unsafe path: '$1'" >&2
            return 1
            ;;
    esac
    case "$1" in
        /*/*) ;;
        *)
            echo "[test] FAIL - work dir must be an absolute path below the root: '$1'" >&2
            return 1
            ;;
    esac
    rm -rf -- "$1"
}

safe_rm_rf "$WORK"
mkdir -p "$WORK/www"
printf 'merecat consumer smoke test\n' > "$WORK/www/index.html"

PORT="${MERECAT_TEST_PORT:-18099}"
"$MERECAT" -n -p "$PORT" -l info -P "$WORK/merecat.pid" "$WORK/www" &
SRV=$!
cleanup() {
    kill "$SRV" 2>/dev/null || true
    wait "$SRV" 2>/dev/null || true
    safe_rm_rf "$WORK" || true
}
trap cleanup EXIT INT TERM

i=0
while [ "$i" -lt 20 ]; do
    if curl -sf "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
        break
    fi
    i=$((i + 1))
    sleep 0.5
done

BODY="$(curl -sS "http://127.0.0.1:$PORT/")"
echo "[test] GET / -> $BODY"
echo "$BODY" | grep -q 'merecat consumer smoke test'

# Regression check for the world-readable contract (see the review of this
# PR): a file the server can read but that is not world-readable must still
# be refused with 403 wherever the file system reports the POSIX "other"
# permission bits.  HMDFS on HarmonyOS PC masks those bits out, so there the
# recipe deliberately falls back to access(2) and serves the file instead;
# the probe below tells the two cases apart.
printf 'top secret\n' > "$WORK/www/secret.html"
chmod 0600 "$WORK/www/secret.html"

# Probe with the same evidence the server uses: a 0777 file placed in
# the served directory; the bits count as visible only when the file
# system reports rwx for others (S_IROTH|S_IXOTH, the server's test).
probe="$WORK/www/perm-probe.html"
: > "$probe"
chmod 0777 "$probe"
# The mode string is the first field of `ls -l` (e.g. -rwxrwxrwx) and its
# 8th-10th characters are the POSIX "other" rwx bits.  The line is matched
# directly, without sed/cut/awk, so the probe needs nothing beyond the shell:
# the previous `sed 's/.* \(...\)$/\1/'` matched the trailing path name
# instead of the mode and therefore reported "hidden" everywhere, which also
# turned the 403 regression below into dead code (PR review 192443231).
probe_line="$(ls -l "$probe" 2>/dev/null || true)"
case "$probe_line" in
    ???????rwx*) other_bits=visible ;;
    *) other_bits=hidden ;;
esac
rm -f "$probe"
echo "[test] POSIX 'other' permission bits reported by the file system: $other_bits"

code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/secret.html")"
if [ "$other_bits" = "visible" ]; then
    if [ "$code" != "403" ]; then
        echo "[test] FAIL - 0600 file answered $code, expected 403 (world-readable contract)"
        exit 1
    fi
    echo "[test] OK - 0600 file readable by the server is still refused (403)"
else
    if [ "$code" != "200" ]; then
        echo "[test] FAIL - 0600 file answered $code, expected the access(2) fallback"
        exit 1
    fi
    echo "[test] OK - 0600 file served through the access(2) fallback ($code)"
fi

echo "[test] OK - packaged merecat serves content over HTTP"
