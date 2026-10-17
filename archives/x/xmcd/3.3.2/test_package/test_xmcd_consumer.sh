#!/usr/bin/env bash
# xmcd 消费者用例（鸿蒙特有，免显示 / headless）
#
# 用法: bash test_xmcd_consumer.sh <bindir>
#
# 上游 xmcd 3.3.2 无测试套件（无 tests/、无 check 目标），本脚本为其消费者侧
# 验证：cda（CLI）的启动横幅/用法输出，以及 xmcd（Motif GUI）在无 X 显示时的
# 启动路径——两者共同证明二进制与其完整动态依赖链可被加载器解析。
# 约束：不使用管道接 head/tail（规避 SIGPIPE），日志落临时文件后读取。
set -euo pipefail

BIN="${1:?usage: test_xmcd_consumer.sh <bindir>}"
WORK="$(mktemp -d)" || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# --- 1. 构建产物存在且可执行 ---------------------------------------------
[ -x "$BIN/cda" ]  || fail "cda binary not found in $BIN"
[ -x "$BIN/xmcd" ] || fail "xmcd binary not found in $BIN"

# --- 2. cda（命令行播放器/抓轨工具）：-h 输出横幅与用法 -------------------
#        退出码非 0 属正常（用法输出后即退出），故不以此判失败。
set +e
"$BIN/cda" -h > "$WORK/cda.log" 2>&1
set -e
grep -q "Error loading shared library" "$WORK/cda.log" \
    && fail "cda loader error: $(cat "$WORK/cda.log")"
grep -q "cda 3.3.2" "$WORK/cda.log" \
    || fail "cda version banner missing: $(cat "$WORK/cda.log")"
grep -q "Usage:" "$WORK/cda.log" \
    || fail "cda usage text missing: $(cat "$WORK/cda.log")"

# --- 3. xmcd（Motif GUI）：无 X 显示时进入显示初始化并报错 ---------------
#        报 "Can't open display" 即证明 Motif/Xt/X11/SM/ICE 依赖链已加载成功
set +e
DISPLAY= "$BIN/xmcd" -h > "$WORK/xmcd.log" 2>&1
set -e
grep -q "Error loading shared library" "$WORK/xmcd.log" \
    && fail "xmcd loader error: $(cat "$WORK/xmcd.log")"
grep -qi "display" "$WORK/xmcd.log" \
    || fail "xmcd did not reach display initialization: $(cat "$WORK/xmcd.log")"

# --- 4. 上游同源工具 gobrowser 存在（CDDB 浏览器，随包投递）--------------
[ -x "$BIN/gobrowser" ] || fail "gobrowser binary not found in $BIN"

echo "PASS: xmcd consumer test (cda CLI banner/usage + xmcd Motif binary load) OK"
