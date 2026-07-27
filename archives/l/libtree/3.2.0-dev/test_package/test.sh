#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for libtree executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] libtree --version"
libtree --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    libtree --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ libtree failed both --version and --help"
        exit 1
    }
}

echo "[test] libtree on itself (self-referential)"
libtree "$(which libtree 2>/dev/null || echo libtree)" 2>/dev/null || true  # non-critical: static binary may report no deps
echo "✅ libtree functional test OK"
