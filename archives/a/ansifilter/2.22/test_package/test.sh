#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ansifilter executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] ansifilter --version"
ansifilter --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    ansifilter --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ ansifilter failed both --version and --help"
        exit 1
    }
}

echo "[test] ansifilter --help"
ansifilter --help > /dev/null 2>&1 && echo "✅ --help OK" || {
    echo "❌ --help failed"
    exit 1
}

echo "[test] ANSI pipe filtering"
echo "$(printf '\033[31mHello\033[0m')" | ansifilter --text > /dev/null 2>&1 && echo "✅ ANSI pipe filtering OK" || {
    echo "❌ ANSI pipe filtering failed"
    exit 1
}

echo ""
echo "All ansifilter smoke tests passed."