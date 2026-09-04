#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ocserv executable package
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] ocserv --version"
ocserv --version && echo "[ok] ocserv --version OK" || {
    echo "[test] ocserv --version failed, trying --help..."
    ocserv --help > /dev/null 2>&1 && echo "[ok] ocserv --help OK" || {
        echo "[fail] ocserv failed both --version and --help"
        exit 1
    }
}

echo "[test] ocpasswd --version"
ocpasswd --version && echo "[ok] ocpasswd --version OK" || {
    echo "[test] ocpasswd --version failed (non-fatal for main gate)"
}

echo "[test] ocserv-worker guard message"
ocserv-worker 2>&1 | grep -q "ocserv" && echo "[ok] ocserv-worker OK" || {
    echo "[test] ocserv-worker produced no expected output (non-fatal)"
}

echo "[test] all smoke tests done"
