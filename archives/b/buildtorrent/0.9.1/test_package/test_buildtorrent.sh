#!/bin/sh
# test_package/test_buildtorrent.sh — buildtorrent 0.9.1 消费者功能测试
#
# 真实执行被测包安装的 bin/buildtorrent 二进制（R34 反空壳），在 $TMPDIR 下
# 完成 5 项内容级功能验证。全部使用 POSIX sh 与 toybox 兼容命令。
# 输出：每个用例一行 [PASS]/[FAIL]，最后一行固定为
#   RESULT: <N> passed, <M> failed
# 由 test_package/conanfile.py 解析后输出 HMBS_TEST_PACKAGE_RESULT 标记。
# 证伪设计：所有内容断言均要求输出文件非空且包含 bencode 关键字；
# 空文件比空文件无法通过（grep 在空文件上失败）。

BIN="${BUILDTORRENT_BIN:-buildtorrent}"
if command -v timeout >/dev/null 2>&1; then
    RUN_BIN="timeout 20 $BIN"
else
    RUN_BIN="$BIN"
fi
BASE="${TMPDIR:-/tmp}/bt-test-$$"

passed=0
failed=0

say() {
    printf '%s\n' "$*"
}

ok() {
    passed=$((passed + 1))
    say "[PASS] $1"
}

ko() {
    failed=$((failed + 1))
    say "[FAIL] $1"
    if [ -f "$BASE/last_log" ]; then
        sed 's/^/       | /' "$BASE/last_log"
    fi
}

finish() {
    trap - 0
    rm -rf "$BASE" 2>/dev/null
    if [ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]; then
        exit 0
    fi
    exit 1
}
trap finish 0

rm -rf "$BASE"
mkdir -p "$BASE/work"

# ---- 用例 1：--version 报告正确版本号 ------------------------------------
$RUN_BIN --version > "$BASE/v.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "0\.9\.1" "$BASE/v.out"; then
    ok "--version reports 0.9.1 ($(head -n 1 "$BASE/v.out"))"
else
    ko "--version output missing '0.9.1' (rc=$rc)"
fi
cp "$BASE/v.out" "$BASE/last_log" 2>/dev/null

# ---- 用例 2：--help 用法输出 --------------------------------------------
$RUN_BIN --help > "$BASE/h.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -qi "usage" "$BASE/h.out" && grep -q "announce" "$BASE/h.out"; then
    ok "--help prints usage with announce option"
else
    ko "--help missing usage/announce (rc=$rc)"
fi
cp "$BASE/h.out" "$BASE/last_log" 2>/dev/null

# ---- 用例 3：单文件 torrent 生成（内容级验证）-----------------------------
printf 'hello buildtorrent content test\n' > "$BASE/work/hello.txt"
$RUN_BIN -a "http://example.com/announce" -D -B "$BASE/work/hello.txt" "$BASE/single.torrent" > "$BASE/c3.log" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$BASE/single.torrent" ] \
   && grep -q "announce" "$BASE/single.torrent" \
   && grep -q "info" "$BASE/single.torrent" \
   && grep -q "pieces" "$BASE/single.torrent"; then
    ok "single-file torrent created with announce/info/pieces ($(wc -c < "$BASE/single.torrent") bytes)"
else
    ko "single-file torrent generation failed or missing bencode keys (rc=$rc)"
fi
cp "$BASE/c3.log" "$BASE/last_log" 2>/dev/null

# ---- 用例 4：确定性字段复现（-d/-B/-D 组合）-------------------------------
$RUN_BIN -a "http://example.com/announce" -d 0 -b "test-creator" "$BASE/work/hello.txt" "$BASE/det1.torrent" > "$BASE/c4a.log" 2>&1
rc1=$?
$RUN_BIN -a "http://example.com/announce" -d 0 -b "test-creator" "$BASE/work/hello.txt" "$BASE/det2.torrent" > "$BASE/c4b.log" 2>&1
rc2=$?
if [ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ] \
   && [ -s "$BASE/det1.torrent" ] && [ -s "$BASE/det2.torrent" ] \
   && cmp -s "$BASE/det1.torrent" "$BASE/det2.torrent" \
   && grep -q "test-creator" "$BASE/det1.torrent"; then
    ok "deterministic rerun with -d/-b reproduces identical torrent"
else
    ko "deterministic rerun mismatch (rc1=$rc1 rc2=$rc2)"
fi
cat "$BASE/c4a.log" "$BASE/c4b.log" > "$BASE/last_log" 2>/dev/null

# ---- 用例 5：magnet 链接输出 ----------------------------------------------
printf 'magnet payload data\n' > "$BASE/work/magnet.txt"
$RUN_BIN -a "http://example.com/announce" -M -D -B "$BASE/work/magnet.txt" "$BASE/mag.torrent" > "$BASE/c5.log" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$BASE/mag.torrent" ] && grep -q "magnet:" "$BASE/c5.log"; then
    ok "magnet link printed for generated torrent"
else
    ko "magnet link missing (rc=$rc)"
fi
cp "$BASE/c5.log" "$BASE/last_log" 2>/dev/null

total=$((passed + failed))
say "RESULT: $passed passed, $failed failed"
finish
