#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ccls executable
# Runs in conanrun env (PATH includes installed bin/ and LD_LIBRARY_PATH the clang/LLVM libs)
set -eu

echo "[test] ccls --version"
ccls --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    ccls --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ ccls failed both --version and --help"
        exit 1
    }
}

# ccls is an LSP server: it must at least print its help to stdout on --help
# (covers the "executable runs without missing shared libraries" requirement).
echo "[test] ccls --help"
ccls --help > /dev/null 2>&1 && echo "✅ --help OK" || {
    echo "❌ ccls --help failed"
    exit 1
}
