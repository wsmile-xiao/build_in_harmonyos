#!/data/service/hnp/bin/bash
# test_dar.sh — functional test for the dar backup tool family.
# Verifies the main dar binary runs and reports its version.
# Argument $1: directory containing the installed binaries (bin/).
set -euo pipefail

BINDIR="$1"
if [ -z "${BINDIR:-}" ] || [ ! -d "$BINDIR" ]; then
    echo "ERROR: binary dir not provided or missing: $BINDIR"
    exit 1
fi

# 诊断：输出 bin/ 目录内容和二进制文件类型，帮助定位安装/链接问题
echo "DEBUG: bin/ contents:"
ls -la "$BINDIR" 2>&1 || true
echo "DEBUG: file types:"
for f in "$BINDIR"/*; do
    [ -f "$f" ] && file "$f" 2>&1 || true
done

# Test 1: dar -V
# 先检查二进制存在且可执行，避免 grep 匹配 bash 错误信息中的路径导致误判通过。
# 注意：不能用 grep -q，它会提前退出导致上游 dar 收到 SIGPIPE（退出码 141），
# 在 set -euo pipefail 下会被判定为测试失败。改用 grep -i > /dev/null 读取全部输入。
if [ ! -x "$BINDIR/dar" ]; then
    echo "FAIL: dar binary missing or not executable"
    echo "DEBUG: ls -la $BINDIR/dar:"
    ls -la "$BINDIR/dar" 2>&1 || true
    exit 1
fi
# 捕获 dar -V 的完整输出用于诊断（|| true 防止 set -e 在非零退出码时退出）
dar_v_output="$("$BINDIR/dar" -V 2>&1)" || true
if echo "$dar_v_output" | grep -i "dar" > /dev/null; then
    echo "PASS: dar -V runs"
else
    echo "FAIL: dar -V did not output expected string"
    echo "DEBUG: dar -V actual output (first 10 lines, may be empty if crashed):"
    echo "$dar_v_output" | head -10 2>&1 || true
    echo "DEBUG: dar binary file type:"
    file "$BINDIR/dar" 2>&1 || true
    echo "DEBUG: ldd $BINDIR/dar:"
    ldd "$BINDIR/dar" 2>&1 || true
    echo "DEBUG: readelf -d $BINDIR/dar (dynamic section):"
    readelf -d "$BINDIR/dar" 2>&1 | head -20 || true
    exit 1
fi

# Test 2: dar -h
# dar 可执行性已在 Test 1 中验证，此处无需重复检查。
dar_help="$( "$BINDIR/dar" -h 2>&1 )" || true
# 同 Test 1/3：用 grep -i > /dev/null 避免 grep -q 提前退出导致 SIGPIPE + pipefail 误判
if echo "$dar_help" | grep -i "dar" > /dev/null; then
    echo "PASS: dar -h runs"
else
    echo "FAIL: dar -h did not output expected string"
    echo "DEBUG: dar -h actual output (first 10 lines):"
    echo "$dar_help" | head -10 2>&1 || true
    exit 1
fi

# Test 3: dar_xform -V (sub-tool)
# 先检查二进制存在性（同 Test 1 理由）
if [ ! -x "$BINDIR/dar_xform" ]; then
    echo "FAIL: dar_xform binary missing or not executable"
    echo "DEBUG: ls -la $BINDIR/dar_xform:"
    ls -la "$BINDIR/dar_xform" 2>&1 || true
    exit 1
fi
# 同上：用 grep -i > /dev/null 避免 SIGPIPE + pipefail 误判
dar_xform_output="$("$BINDIR/dar_xform" -V 2>&1)" || true
if echo "$dar_xform_output" | grep -i "dar" > /dev/null; then
    echo "PASS: dar_xform -V runs"
else
    echo "FAIL: dar_xform -V did not output expected string"
    echo "DEBUG: dar_xform -V actual output (first 10 lines):"
    echo "$dar_xform_output" | head -10 2>&1 || true
    exit 1
fi

# Test 4: dar_manager -V (sub-tool)
# 先检查二进制存在性（同 Test 1 理由）
if [ ! -x "$BINDIR/dar_manager" ]; then
    echo "FAIL: dar_manager binary missing or not executable"
    echo "DEBUG: ls -la $BINDIR/dar_manager:"
    ls -la "$BINDIR/dar_manager" 2>&1 || true
    exit 1
fi
# 同上：用 grep -i > /dev/null 避免 SIGPIPE + pipefail 误判
dar_manager_output="$("$BINDIR/dar_manager" -V 2>&1)" || true
if echo "$dar_manager_output" | grep -i "dar" > /dev/null; then
    echo "PASS: dar_manager -V runs"
else
    echo "FAIL: dar_manager -V did not output expected string"
    echo "DEBUG: dar_manager -V actual output (first 10 lines):"
    echo "$dar_manager_output" | head -10 2>&1 || true
    exit 1
fi

# Test 5: dar_cp -V (sub-tool)
# 先检查二进制存在性（同 Test 1 理由）
if [ ! -x "$BINDIR/dar_cp" ]; then
    echo "FAIL: dar_cp binary missing or not executable"
    echo "DEBUG: ls -la $BINDIR/dar_cp:"
    ls -la "$BINDIR/dar_cp" 2>&1 || true
    exit 1
fi
# 同上：用 grep -i > /dev/null 避免 SIGPIPE + pipefail 误判
dar_cp_output="$("$BINDIR/dar_cp" -V 2>&1)" || true
if echo "$dar_cp_output" | grep -i "dar" > /dev/null; then
    echo "PASS: dar_cp -V runs"
else
    echo "FAIL: dar_cp -V did not output expected string"
    echo "DEBUG: dar_cp -V actual output (first 10 lines):"
    echo "$dar_cp_output" | head -10 2>&1 || true
    exit 1
fi

# Test 6: dar_slave -V (sub-tool)
if [ ! -x "$BINDIR/dar_slave" ]; then
    echo "FAIL: dar_slave binary missing or not executable"
    echo "DEBUG: ls -la $BINDIR/dar_slave:"
    ls -la "$BINDIR/dar_slave" 2>&1 || true
    exit 1
fi
dar_slave_output="$("$BINDIR/dar_slave" -V 2>&1)" || true
if echo "$dar_slave_output" | grep -i "dar" > /dev/null; then
    echo "PASS: dar_slave -V runs"
else
    echo "FAIL: dar_slave -V did not output expected string"
    echo "DEBUG: dar_slave -V actual output (first 10 lines):"
    echo "$dar_slave_output" | head -10 2>&1 || true
    exit 1
fi

# Test 7: dar_split -V (sub-tool)
if [ ! -x "$BINDIR/dar_split" ]; then
    echo "FAIL: dar_split binary missing or not executable"
    echo "DEBUG: ls -la $BINDIR/dar_split:"
    ls -la "$BINDIR/dar_split" 2>&1 || true
    exit 1
fi
dar_split_output="$("$BINDIR/dar_split" -V 2>&1)" || true
if echo "$dar_split_output" | grep -i "dar" > /dev/null; then
    echo "PASS: dar_split -V runs"
else
    echo "FAIL: dar_split -V did not output expected string"
    echo "DEBUG: dar_split -V actual output (first 10 lines):"
    echo "$dar_split_output" | head -10 2>&1 || true
    exit 1
fi

echo "ALL TESTS PASSED"
