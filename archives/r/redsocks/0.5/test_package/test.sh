#!/data/service/hnp/bin/bash
# test_package/test.sh — redsocks 0.5 smoke test.
# Runs in the conanrun env: PATH includes the installed bin/ and
# LD_LIBRARY_PATH covers the shared libevent libs (run=True on the require).
set -euo pipefail

# Writable scratch dir — /tmp is read-only on OHOS (E002)
WORK="$(mktemp -d "${TMPDIR:-/tmp}/redsocks-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

echo "[step] redsocks -v version check"
redsocks -v > version-output.txt 2>&1
grep -q "redsocks" version-output.txt || {
    echo "[fail] redsocks -v did not print version information"
    cat version-output.txt
    exit 1
}

echo "[step] redsocks -t config syntax check (valid config)"
cat > "$WORK/redsocks-test.conf" << 'CONFEOF'
base {
    log_debug = off;
    log_info = on;
    log = "file:/dev/null";
    daemon = off;
    user = redsocks;
    group = redsocks;
    redirector = iptables;
}
redsocks {
    local_ip = 127.0.0.1;
    local_port = 12345;
    ip = 127.0.0.1;
    port = 1080;
    type = socks5;
}
CONFEOF
# -t validates config syntax and exits 0 silently on success
redsocks -t -c "$WORK/redsocks-test.conf"
echo "[ok] valid config accepted"

echo "[step] redsocks -t rejects invalid config"
echo "garbage {" > "$WORK/bad.conf"
if redsocks -t -c "$WORK/bad.conf" > bad-output.txt 2>&1; then
    echo "[fail] redsocks -t accepted an invalid config"
    exit 1
fi
echo "[ok] invalid config rejected"

echo "[ok] all smoke tests passed"
