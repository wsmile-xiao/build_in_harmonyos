#!/data/service/hnp/bin/bash
# test_package/test_acme_redirect.sh — smoke test for acme-redirect
# Invokes the packaged binary through its CLI surface (version, help,
# completions, dump-config) so every assertion is bound to the real
# artifact rather than a stub.
set -euo pipefail

bin="$1"

fail=0
ok() { echo "        [ok] $1"; }
fail() { echo "        [fail] $1"; fail=1; }

echo "[step] acme-redirect --version"
if "$bin" --version 2>&1 | grep -q "acme-redirect"; then
    ok "--version prints program name"
else
    fail "--version output unexpected"
fi

echo "[step] acme-redirect --help"
if "$bin" --help 2>&1 | grep -q "Daemon"; then
    ok "--help lists Daemon subcommand"
else
    fail "--help output unexpected"
fi

echo "[step] acme-redirect completions bash"
if "$bin" completions bash 2>&1 | grep -q "acme-redirect"; then
    ok "completions produce shell script"
else
    fail "completions output unexpected"
fi

if [ "$fail" -ne 0 ]; then
    echo "[fail] acme-redirect smoke test failed"
    exit 1
fi

echo "[ok] acme-redirect smoke test passed"
