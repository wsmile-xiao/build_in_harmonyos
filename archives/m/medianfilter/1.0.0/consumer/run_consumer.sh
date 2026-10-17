#!/usr/bin/env bash
# consumer — medianfilter 1.0.0 消费者验证构建/运行脚本
#
# 从最终 Conan 包编译并运行消费者用例：
#   clang -I<include> consumer_sensor.c <lib>/libmedianfilter.a
# 用法: bash run_consumer.sh <package_folder>
set -euo pipefail
PKG="${1:?usage: run_consumer.sh <package_folder>}"
CC="${CC:-/data/service/hnp/bin/clang}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/medianfilter-consumer.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM

"$CC" -O2 -std=c11 -Wall -Wextra -Werror -I"$PKG/include" \
    "$(dirname "$0")/consumer_sensor.c" "$PKG/lib/libmedianfilter.a" \
    -o "$WORK/consumer_sensor.ohos"
"$WORK/consumer_sensor.ohos"