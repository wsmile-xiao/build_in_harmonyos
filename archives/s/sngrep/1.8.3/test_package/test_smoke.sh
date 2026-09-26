#!/bin/sh
# sngrep 消费者冒烟（R34）——真实执行被测包安装的 sngrep 二进制。
# 用法: test_smoke.sh <sngrep> <workdir> <ipip.pcap>
# （二进制夹具不入仓：ipip.pcap.b64 由 conanfile.py 运行期解码后传入路径，
#   规避平台 git-am checkout 缺 --binary 的 patch does not apply）
set -eu
SNGREP="$1"; WORK="$2"; PCAP="$3"
mkdir -p "$WORK"

"$SNGREP" --version > "$WORK/version.out" 2>&1
grep -q "1.8.3" "$WORK/version.out" || { echo "FAIL: version"; cat "$WORK/version.out"; exit 1; }

"$SNGREP" --help > "$WORK/help.out" 2>&1
grep -q "Usage" "$WORK/help.out" || { echo "FAIL: help"; cat "$WORK/help.out"; exit 1; }

"$SNGREP" -N -I "$PCAP" > "$WORK/pcap.out" 2>&1
grep -q "Dialog count: 1" "$WORK/pcap.out" || { echo "FAIL: pcap"; tail -5 "$WORK/pcap.out"; exit 1; }

echo "test_smoke.sh: 3/3 assertions passed (version / help / pcap-dialog-count)"
