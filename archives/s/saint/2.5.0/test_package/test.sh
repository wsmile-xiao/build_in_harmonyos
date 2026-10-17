#!/bin/sh
# test_package/test.sh — saint 2.5.0 命令行工具功能验证。
#
# 在 conanrun 环境（PATH 含 saint bin、LD_LIBRARY_PATH 含 gsl lib）中执行。
# BINDIR（argv $1）由 test_package/conanfile.py 从 saint package_folder 解析传入。
#
# 断言（全部可证伪，harness 能抓到失败）：
#   1-5. 五个 saint 可执行均已安装且可执行
#   6.  saint-reformat -v 输出 "SAINT version 2.5.0"
#   7.  saint-reformat 用最小真实 AP-MS 输入集完成数据重排，生成非空 interaction.new
#   8-11. 另外四个 MCMC 工具以过少参数触发 usage（可执行且成功拉起 GSL RNG）
#
# 输出 HMBS 机器证据标记（硬门禁）：
#   HMBS_UPSTREAM_TEST_RESULT  — saint 上游无测试框架（audit，no_tests）
#   HMBS_TEST_PACKAGE_RESULT   — 上述 11 项真实断言计数
set -e

BINDIR="${1:-}"

# HMBS readonly_tmp：真机 /tmp 只读(erofs)，且 /bin/sh 在硬编码 /tmp 上做
# 命令替换临时文件（忽略 TMPDIR）。本脚本刻意使用零 $(...) / 反引号。
# 优先复用 hmbs 注入的可写 TMPDIR/TMP/TEMP。
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR TMP TEMP

# 运行工作目录：saint-reformat 会在 cwd 写 interaction.new/prey.new/interaction.intermediate
# 并 system("mkdir reformat_log")，必须用可写目录。
WORKDIR="$TMPDIR/saint_work"
rm -rf "$WORKDIR" 2>/dev/null || true
mkdir -p "$WORKDIR" 2>/dev/null || true

# 工具解析：优先 argv BINDIR，否则 PATH。
resolve_tool() {
    # $1 = tool name；回显绝对路径到 $TMPDIR/toolpath.txt
    _t="$1"
    if [ -n "$BINDIR" ] && [ -f "$BINDIR/$_t" ]; then
        echo "$BINDIR/$_t" > "$TMPDIR/toolpath.txt"
    elif [ -f "/data/service/hnp/bin/$_t" ]; then
        echo "/data/service/hnp/bin/$_t" > "$TMPDIR/toolpath.txt"
    else
        echo "" > "$TMPDIR/toolpath.txt"
    fi
}

# 探测二进制是否可执行
is_runable() {
    # $1 = 绝对路径；0=可执行 1=否
    _p="$1"
    if [ -n "$_p" ] && [ -f "$_p" ]; then
        if [ -x "$_p" ] || [ "${HMBS_CAP_CHMOD}" = "0" ]; then
            return 0
        fi
        # 不可执行位但机器可运行：直接尝试
        if "$_p" > /dev/null 2>&1; then
            return 0
        fi
        return 1
    fi
    return 1
}

TOOLS="saint-reformat saint-spc-noctrl saint-spc-noctrl-matrix saint-spc-ctrl saint-int-ctrl"

PASS_COUNT=0

echo "[test] bindir='${BINDIR:-}'"
echo "[test] TMPDIR=$TMPDIR"

# ── 断言 1-5：五个二进制已安装且可执行 ──
for t in $TOOLS; do
    resolve_tool "$t"
    if read -r T < "$TMPDIR/toolpath.txt" && [ -n "$T" ] && [ -f "$T" ]; then
        if is_runable "$T"; then
            echo "[test] PASS: $t installed/runnable ($T)"
            PASS_COUNT=$((PASS_COUNT+1))
        else
            echo "[test] FAIL: $t not runnable ($T)" >&2
        fi
    else
        echo "[test] FAIL: $t not found in bin" >&2
    fi
done

# ── 断言 6：saint-reformat -v ──
echo "[test] run: saint-reformat -v"
if [ -n "$BINDIR" ]; then
    "$BINDIR/saint-reformat" -v > "$TMPDIR/ver_out.txt" 2>&1 || true
else
    saint-reformat -v > "$TMPDIR/ver_out.txt" 2>&1 || true
fi
cat "$TMPDIR/ver_out.txt" || true
if grep -q "SAINT version 2.5.0" "$TMPDIR/ver_out.txt" 2>/dev/null; then
    echo "[test] PASS: saint-reformat -v reports 2.5.0"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: saint-reformat -v version string missing" >&2
fi

# ── 断言 7：saint-reformat 最小真实数据重排 ──
echo "[test] run: saint-reformat on crafted AP-MS data"
cat > "$WORKDIR/interaction.txt" <<'EOF'
IP1	BaitA	Prey1	10
IP1	BaitA	Prey2	5
EOF
cat > "$WORKDIR/prey.txt" <<'EOF'
Prey1	100	GeneX
Prey2	200	GeneY
EOF
cat > "$WORKDIR/bait.txt" <<'EOF'
IP1	BaitA	T
EOF
(cd "$WORKDIR" && "$BINDIR/saint-reformat" interaction.txt prey.txt bait.txt) > "$TMPDIR/reformat_out.txt" 2>&1 || true
cat "$TMPDIR/reformat_out.txt" || true
# 校验 interaction.new 非空且含预期重排行
RFOK=0
if [ -s "$WORKDIR/interaction.new" ] 2>/dev/null; then
    grep -q "IP1" "$WORKDIR/interaction.new" 2>/dev/null && RFOK=1
fi
if [ "$RFOK" = "1" ]; then
    echo "[test] PASS: saint-reformat produced interaction.new"
    echo "[test] interaction.new content:"
    cat "$WORKDIR/interaction.new" || true
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test] FAIL: saint-reformat interaction.new missing/empty/wrong" >&2
    ls -la "$WORKDIR" >&2 2>/dev/null || true
fi

# ── 断言 8-11：四个 MCMC 工具以过少参数触发 usage（执行 + GSL 拉起）──
for t in saint-spc-noctrl saint-spc-ctrl saint-int-ctrl saint-spc-noctrl-matrix; do
    echo "[test] run: $t (usage, no args)"
    if [ -n "$BINDIR" ]; then
        "$BINDIR/$t" > "$TMPDIR/usage_out.txt" 2>&1 || true
    else
        "$t" > "$TMPDIR/usage_out.txt" 2>&1 || true
    fi
    cat "$TMPDIR/usage_out.txt" || true
    # 过少参数应打印 usage 并返回非 0；能走到 commandLine 即证明 GSL 链接可运行。
    if grep -qi "usage" "$TMPDIR/usage_out.txt" 2>/dev/null; then
        echo "[test] PASS: $t executed and printed usage"
        PASS_COUNT=$((PASS_COUNT+1))
    else
        echo "[test] FAIL: $t did not print usage" >&2
    fi
done

# ── 上游审计标记（authority: test_package/MANIFEST.yml）──
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"saint 2.5.0 ships no upstream test suite: no test/tests dir, no make check target, no gtest/pytest/criterion bindings.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

if [ "$PASS_COUNT" -eq 11 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":11,"passedCount":11}'
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh\",\"discovered\":11,\"passedCount\":$PASS_COUNT}"
    exit 1
fi
