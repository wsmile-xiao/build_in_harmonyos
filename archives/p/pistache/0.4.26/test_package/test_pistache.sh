#!/usr/bin/env bash
# pistache 消费者测试驱动 —— 真实执行安装后产物。
#
# 定位方式：上游 Meson 安装只提供 pkg-config 元数据（lib/pkgconfig/libpistache.pc），
# 不生成 CMake config，因此这里用 pkg-config 取编译与链接参数，而不是 find_package。
# 断言：编译退出码为 0、运行退出码为 0、输出包含断言行且 failed=0。
#
# 用法：test_pistache.sh [PKG_CONFIG_PATH] [CXX]
#   $1 pkg-config 搜索路径（可用 : 分隔多个）；缺省沿用环境变量
#   $2 C++ 编译器；缺省用 $CXX 或 c++
# 不写 /tmp（设备上只读），工作目录建在当前工作目录下。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${1:-}" != "" ]; then
    PKG_CONFIG_PATH="$1"
    export PKG_CONFIG_PATH
fi
CXX_BIN="${2:-${CXX:-c++}}"

echo "PKG_CONFIG_PATH=${PKG_CONFIG_PATH:-<unset>}"
echo "using CXX: ${CXX_BIN}"

if ! command -v pkg-config >/dev/null 2>&1; then
    echo "FAIL: pkg-config 不可用" >&2
    exit 1
fi

if ! pkg-config --exists libpistache; then
    echo "FAIL: pkg-config 找不到 libpistache；已试路径=${PKG_CONFIG_PATH:-<unset>}" >&2
    echo "  搜索到的 .pc 文件：" >&2
    ls -la ${PKG_CONFIG_PATH:+$(echo "$PKG_CONFIG_PATH" | tr ':' ' ')} 2>/dev/null | grep -i pistache || echo "  （无 pistache .pc）" >&2
    exit 1
fi

echo "libpistache version: $(pkg-config --modversion libpistache)"
echo "libpistache cflags : $(pkg-config --cflags libpistache)"
echo "libpistache libs   : $(pkg-config --libs libpistache)"

WORK="$(pwd)/pistache-consumer-check"
rm -rf "$WORK"
mkdir -p "$WORK"
BIN="$WORK/test_consumer"

# shellcheck disable=SC2046
"$CXX_BIN" -std=c++17 -Wall -o "$BIN" "$HERE/test_consumer.cpp" \
    $(pkg-config --cflags --libs libpistache)

if [ ! -x "$BIN" ]; then
    echo "FAIL: 消费者程序未产出可执行文件" >&2
    exit 1
fi

OUT="$WORK/consumer.out"
"$BIN" | tee "$OUT"

if ! grep -q "pistache consumer: checks=" "$OUT"; then
    echo "FAIL: 输出缺少断言统计行" >&2
    exit 1
fi

if ! grep -q "failed=0" "$OUT"; then
    echo "FAIL: 存在失败断言" >&2
    exit 1
fi

echo "test_pistache.sh: PASS"
