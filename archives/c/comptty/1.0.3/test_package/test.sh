#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the comptty executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] comptty --version"
OUT=$(comptty --version 2>&1) || { echo "FAIL: --version rc=$?"; exit 1; }
echo "  output: $OUT"
echo "$OUT" | grep -q "Version:" || { echo "FAIL: --version 未输出 Version 信息"; exit 1; }
echo "$OUT" | grep -q "1.0.3" || { echo "FAIL: --version 未包含版本号 1.0.3"; exit 1; }
echo "OK: --version returns version info"

echo "[test] comptty --help"
OUT=$(comptty --help 2>&1) || { echo "FAIL: --help rc=$?"; exit 1; }
echo "$OUT" | grep -q "\-\-version" || { echo "FAIL: --help 未列出 --version 选项"; exit 1; }
echo "$OUT" | grep -q "\-\-help" || { echo "FAIL: --help 未列出 --help 选项"; exit 1; }
echo "OK: --help lists CLI options"

echo "[test] comptty 链接期 FLTK 符号检查（R40 补充）"
# 沙箱无 X display 无法运行 GUI 路径（Fl_Window 构造需显示环境），
# 补充链接期静态符号检查验证 FLTK 库已正确链接进可执行文件：
# 上游 libfltk 为静态库（archives/l/libfltk 配方 shared=False），
# FLTK 符号（Fl_Window 等）被静态嵌入二进制，动态 NEEDED 表中
# 不可见，须用 nm 检查静态符号（readelf -d 只能看到 libX11.so.6
# 等动态依赖）。与 libfltk 已合入配方（FLTK_BUILD_TEST=ON 构建即
# 验证编译链接）同款思路。
BIN=$(command -v comptty)
if [ -z "$BIN" ]; then echo "FAIL: 未找到 comptty 可执行文件"; exit 1; fi
if command -v nm >/dev/null 2>&1; then
    N_FLTK=$(nm "$BIN" 2>/dev/null | grep -c "Fl_Window" || true)
    if [ "$N_FLTK" -ge 1 ]; then
        echo "OK: comptty 已静态链接 FLTK（检出 $N_FLTK 个 Fl_Window 符号）"
    else
        echo "FAIL: comptty 未检出 FLTK 符号（Fl_Window）"
        exit 1
    fi
else
    echo "WARN: nm 不可用，跳过链接期符号检查（非阻塞）"
fi

echo "comptty test_package PASS"
