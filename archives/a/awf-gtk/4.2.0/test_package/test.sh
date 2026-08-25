#!/data/service/hnp/bin/bash
# test_package/test.sh — awf-gtk 4.2.0 executable smoke test.
# Runs `awf-gtk4 --version` and asserts the output contains "4.2.0".
# The binary is passed as $1 (absolute path inside the conan package bin/).
# LD_LIBRARY_PATH is provided by the test_package conanfile (GTK4 system prefix).
set -u

BIN="${1:?usage: test.sh <path-to-awf-gtk4>}"

# 强制 external（含签名的新版 glib/pango/libintl/libnotify）最优先。
# conanrun 自动生成的 LD_LIBRARY_PATH 会把 conan 缓存的旧 glib(2.84) 前置，
# 遮蔽 external 里的 glib 2.88，导致 libgtk-4 重定位缺符号。
PREFIX="${GTK_PREFIX:-${DEFAULT_PREFIX:-/storage/Users/currentUser/usr/local}}"
export LD_LIBRARY_PATH="${PREFIX}/lib/external:${PREFIX}/lib:${LD_LIBRARY_PATH:-}"

if [ ! -x "$BIN" ]; then
    echo "❌ awf-gtk4 not found or not executable: $BIN"
    exit 1
fi

echo "[test] $BIN --version"
OUT="$("$BIN" --version 2>&1)"
RC=$?

if [ $RC -ne 0 ]; then
    echo "❌ awf-gtk4 --version exited with code $RC"
    echo "   output: $OUT"
    # ── 运行时诊断（CI test() 阶段库加载失败定位用）──
    echo "=== runtime diagnostic ==="
    echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
    echo "--- external dir ---"
    ls -la "${PREFIX}/lib/external/" 2>/dev/null | grep -E "libglib|libz\.so|libpng|libnotify|libgtk|libpango|libcairo|libgdk" | head -12
    echo "--- lib top-level dir ---"
    ls -la "${PREFIX}/lib/" 2>/dev/null | grep -E "libglib|libz\.so|libpng|libnotify|libgtk|libpango|libcairo|libgdk" | head -12
    echo "--- ldd the binary ---"
    ldd "$BIN" 2>&1 | grep -iE "not found|libglib|libz\.so|libpng|libnotify" | head -10 || true
    exit 1
fi

echo "   output: $OUT"

if echo "$OUT" | grep -q "4\.2\.0"; then
    echo "✅ awf-gtk4 --version contains 4.2.0"
    exit 0
else
    echo "❌ awf-gtk4 --version output does not contain 4.2.0"
    exit 1
fi
