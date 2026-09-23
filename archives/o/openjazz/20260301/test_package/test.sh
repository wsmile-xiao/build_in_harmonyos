#!/data/service/hnp/bin/bash
# test_package/test.sh — OpenJazz 消费者冒烟测试（OHOS 无头安全路径）
# Usage: test.sh <OpenJazz binary path>
#
# 全部断言只走 argparse 的纯 IO 退出路径：-v/--version 由 version_cb 打印
# 版本后 exit(EXIT_SUCCESS)，--help 由 OPT_HELP 打印 usage 后退出；两者都在
# startUp()（SDL 视频/音频初始化）之前 return，无头环境不会触达显示设备。
# R34: 真实执行被测包二进制并断言输出。
set -eu

EXE="${1:?usage: test.sh <OpenJazz binary path>}"

# OpenJazz 会在 cwd 写 openjazz.log；切到二进制所在临时目录，避免污染配方目录
cd "$(dirname "$EXE")"

echo "[1/4] 二进制存在且可执行"
test -x "$EXE"
echo "OK: $EXE 存在且可执行"

echo "[2/4] OpenJazz -v"
OUT="$("$EXE" -v)"
echo "$OUT"
echo "$OUT" | grep -q "OpenJazz 20260301"
echo "OK: -v 输出版本 OpenJazz 20260301（rc=0）"

echo "[3/4] OpenJazz --version"
OUT="$("$EXE" --version)"
echo "$OUT"
echo "$OUT" | grep -q "OpenJazz 20260301"
echo "OK: --version 输出版本 OpenJazz 20260301（rc=0）"

echo "[4/4] OpenJazz --help"
OUT="$("$EXE" --help)"
echo "$OUT"
echo "$OUT" | grep -q "Usage: OpenJazz"
echo "$OUT" | grep -q "Engine options"
echo "OK: --help 输出 usage 与 Engine options（rc=0）"
