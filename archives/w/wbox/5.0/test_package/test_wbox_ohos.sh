#!/usr/bin/env bash
# test_wbox_ohos.sh — HarmonyOS PC (aarch64, musl) specific verification for wbox 5.
#
# Upstream wbox has no automated test suite, and its own project page only
# documents manual usage.  This script is the HarmonyOS-specific layer: it
# proves that a wbox built for OHOS is a well-formed OHOS executable AND that
# the POSIX surface wbox depends on actually behaves on OHOS (loopback sockets,
# fork() per-connection children, signal handling, process exit codes).
#
# T1  ELF64 AArch64 + PIE (ET_DYN)
# T2  musl dynamic loader, no glibc linkage
# T3  no host build path (/storage/, /home/, /Users/) leaked into the binary
# T4  non-executable stack (GNU_STACK RW)
# T5  end-to-end HTTP round trip:
#       T5a servermode serves a file: HTTP 200 + payload match + real client mode
#       T5b missing file -> 404 Not Found
#       T5c `clients 2` (fork) concurrency on OHOS
#       T5d connection refused -> exit code 3 (WBOX_EXIT_CONN)
#       T5e server log records a successfully served connection
#
# usage: test_wbox_ohos.sh [path-to-wbox-binary]
set -euo pipefail

WBOX_BIN="${1:-${WBOX_BIN:-wbox}}"
fail=0
ok()  { echo "  [PASS] $1"; }
bad() { echo "  [FAIL] $1"; fail=1; }

echo "== wbox HarmonyOS-specific test =="
echo "binary: $WBOX_BIN"

# ── T1/T2/T4: executable format, loader and hardening ────────────────
hdr=$(readelf -h "$WBOX_BIN")
echo "$hdr" | grep -q "AArch64" && ok "T1 ELF machine = AArch64" || bad "T1 machine is not AArch64"
echo "$hdr" | grep -q "DYN" && ok "T1 PIE (ET_DYN)" || bad "T1 not position independent"

interp=$(readelf -lW "$WBOX_BIN" | sed -n 's/.*Requesting program interpreter: \(.*\)]/\1/p')
case "$interp" in
    *ld-musl-aarch64.so.1*) ok "T2 musl loader: $interp" ;;
    *) bad "T2 unexpected dynamic loader: $interp" ;;
esac
if readelf -d "$WBOX_BIN" | grep -qiE "libc\.so\.6|ld-linux"; then
    bad "T2 glibc linkage found"
else
    ok "T2 no glibc linkage"
fi

stack=$(readelf -lW "$WBOX_BIN" | awk '/GNU_STACK/{print $7}')
if [ "$stack" = "RW" ]; then
    ok "T4 non-executable stack (GNU_STACK RW)"
else
    bad "T4 GNU_STACK is '$stack' (expected RW)"
fi

if strings "$WBOX_BIN" | grep -qE "/storage/|/home/|/Users/"; then
    bad "T3 host build path leaked into binary"
else
    ok "T3 no host build path in binary"
fi

# ── T5: real HTTP server + client round trip ────────────────────────
tmp=$(mktemp -d "${TMPDIR:-/tmp}/wbox-ohos-XXXXXX")
port=$(( 20000 + (RANDOM % 20000) ))
payload="wbox-ohos-payload-$$"
mkdir -p "$tmp/webroot"
printf '%s\n' "$payload" > "$tmp/webroot/index.html"
srv_pid=""
cleanup() {
    [ -n "$srv_pid" ] && kill "$srv_pid" 2>/dev/null || true
    rm -rf "$tmp"
}
trap cleanup EXIT

"$WBOX_BIN" servermode webroot "$tmp/webroot" serverport "$port" >"$tmp/server.log" 2>&1 &
srv_pid=$!
sleep 2

# T5a: 200 + body served back through the real client mode
body=$("$WBOX_BIN" "127.0.0.1:$port/index.html" 1 showhdr dump 2>&1 || true)
if printf '%s' "$body" | grep -q "200 OK"; then
    ok "T5a HTTP 200 from servermode"
else
    bad "T5a no 200 OK: $(printf '%s' "$body" | head -3)"
fi
if printf '%s' "$body" | grep -q "$payload"; then
    ok "T5a payload served back intact ($payload)"
else
    bad "T5a payload missing from reply body"
fi

# T5b: 404 for a path that does not exist
notfound=$("$WBOX_BIN" "127.0.0.1:$port/definitely-missing.txt" 1 2>&1 || true)
if printf '%s' "$notfound" | grep -q "404 Not Found"; then
    ok "T5b missing file -> 404 Not Found"
else
    bad "T5b expected 404, got: $(printf '%s' "$notfound" | head -3)"
fi

# T5c: fork()-based concurrency (2 clients x 3 requests)
conc=$("$WBOX_BIN" "127.0.0.1:$port/index.html" 3 clients 2 2>&1 || true)
ok_replies=$(printf '%s\n' "$conc" | grep -c "200 OK" || true)
if [ "${ok_replies:-0}" -ge 3 ] && printf '%s' "$conc" | grep -q "replies received"; then
    ok "T5c clients 2 (fork) -> ${ok_replies} x 200 OK replies"
else
    bad "T5c concurrency: $(printf '%s' "$conc" | tail -2 | tr '\n' ' ')"
fi

# T5d: exit-code contract on connection refused (WBOX_EXIT_CONN = 3)
set +e
"$WBOX_BIN" "127.0.0.1:1" 1 >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -eq 3 ]; then
    ok "T5d connection refused -> exit 3"
else
    bad "T5d expected exit 3, got $rc"
fi

# T5e: server-side log proves the fork child handled the connection
if grep -q "served with success" "$tmp/server.log"; then
    ok "T5e server log records successful serving"
else
    bad "T5e server log has no success record"
fi

if [ "$fail" -ne 0 ]; then
    echo "== OHOS test FAILED =="
    exit 1
fi
echo "== OHOS test PASSED =="
