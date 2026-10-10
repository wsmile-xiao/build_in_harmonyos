#!/usr/bin/env bash
# xli 消费者用例（鸿蒙特有，免显示 / headless）
#
# 用法: bash test_xli_consumer.sh <bindir>
#
# 上游 xli 1.17.0 无测试套件（无 tests/、无 check 目标），本脚本为其消费者侧
# 验证：覆盖 xlito 的文件读写功能与 xli 二进制的启动/依赖链加载。
# 约束：安全模式 set -euo pipefail；不使用管道接 head/tail（规避 SIGPIPE），
#       日志落临时文件后读取。
set -euo pipefail

BIN="${1:?usage: test_xli_consumer.sh <bindir>}"
WORK="$(mktemp -d)" || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# --- 1. 构建产物存在且可执行 ---------------------------------------------
[ -x "$BIN/xli" ]   || fail "xli binary not found in $BIN"
[ -x "$BIN/xlito" ] || fail "xlito binary not found in $BIN"

# --- 2. 生成最小 PPM 样本（P3 纯文本，避免仓库携带二进制样本文件）-------
printf 'P3\n2 2\n255\n255 0 0   0 255 0\n0 0 255   255 255 255\n' > "$WORK/sample.ppm" \
    || fail "cannot create sample image"

# --- 3. xlito：把 xli 选项块嵌入图片文件（真实文件 I/O，免显示）--------
"$BIN/xlito" -c '-delay 5' "$WORK/sample.ppm" > "$WORK/embed.log" 2>&1 \
    || fail "xlito embed failed: $(cat "$WORK/embed.log")"

# --- 4. xlito：读回选项块，必须包含刚写入的内容 --------------------------
"$BIN/xlito" -x "$WORK/sample.ppm" > "$WORK/extract.log" 2>&1 \
    || fail "xlito extract failed: $(cat "$WORK/extract.log")"
grep -q -- '-delay 5' "$WORK/extract.log" \
    || fail "embedded options not round-tripped: $(cat "$WORK/extract.log")"

# --- 5. xli：交互帮助设施中查询选项表（不建立 X 连接），验证二进制与依赖链可加载
#        `?` 列出全部选项名，退出命令为 `quit`
printf '?\nquit\n' | "$BIN/xli" -help > "$WORK/help.log" 2>&1 \
    || fail "xli -help execution failed"
grep -qi 'xli' "$WORK/help.log" || fail "xli usage banner missing"
grep -qi 'display' "$WORK/help.log" || fail "xli option table missing ('display')"
grep -qi 'verbose' "$WORK/help.log" || fail "xli option table incomplete ('verbose')"

echo "PASS: xli consumer test (xlito round-trip + xli startup) OK"
