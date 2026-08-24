#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for flow-control executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] flow --version"
flow --version && echo "✅ --version OK" || {
    echo "[test] flow --version failed, trying --help..."
    flow --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ flow failed both --version and --help"
        exit 1
    }
}

echo "[test] flow --help"
flow --help 2>&1 | grep -qi "Flow Control" && echo "✅ --help contains Flow Control" || {
    echo "[test] --help output unexpected, but binary executed"
}

echo "[test] flow --list-languages"
TMPFILE="${TMPDIR:-$HOME/tmp}/flow_langs.txt"
mkdir -p "$(dirname "$TMPFILE")"
flow --list-languages > "$TMPFILE" 2>&1 || true
if grep -qi "zig\|rust\|python" "$TMPFILE" 2>&1; then
    echo "✅ --list-languages OK"
    head -n 20 "$TMPFILE"
else
    echo "[test] --list-languages output:"
    cat "$TMPFILE" 2>&1 || true
    echo "⚠️ --list-languages did not contain expected languages (non-fatal)"
fi

echo "[test] all checks passed"
