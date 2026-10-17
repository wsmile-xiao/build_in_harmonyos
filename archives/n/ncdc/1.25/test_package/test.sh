#!/bin/sh
# test.sh — ncdc 1.25 消费者断言（7 项）
# 用法: sh test.sh <ncdc-binary> <writable-workdir>
#
# 上游无测试套件，故此处对**打包后的真实二进制**做实跑断言：
# `--version` 由 src/main.c 的 print_version() 输出编译期/运行期库版本，
# 逐项比对即可同时证明
#   (a) 二进制在 OHOS 上可执行（动态加载器成功解析全部 NEEDED）；
#   (b) 运行期加载的是**本配方打包的** conan 依赖，而非设备上的同名系统库
#       （编译期与运行期版本逐一相等才是同一份制品）——这是鸿蒙特有断言；
#   (c) 可选依赖 geoip/libloc 按预期关闭，未误探测到宿主库。
set -e

NCDC="$1"
WORK="$2"
fail=0

check() {
    # check <描述> <文件> <grep 模式>
    if grep -q "$3" "$2"; then
        echo "ok - $1"
    else
        echo "FAIL - $1"
        fail=1
    fi
}

cd "$WORK"

# 0) 二进制存在且可执行
if [ -x "$NCDC" ]; then
    echo "ok - bin/ncdc 存在且可执行"
else
    echo "FAIL - bin/ncdc 不存在或不可执行"
    fail=1
fi

"$NCDC" --version > version.out 2> version.err || {
    echo "FAIL - ncdc --version 非零退出（OHOS 上加载共享依赖失败）"
    cat version.err
    fail=1
}

# 1) 自身版本取自 AC_INIT（--disable-git-version）
check "自身版本为 1.25" version.out "ncdc 1.25 (built "

# 2)-4) 编译期版本 == 运行期版本 → 证明加载的是打包的 conan 制品
check "GLib 编译期==运行期 2.84.0"  version.out "GLib 2\.84\.0 (2\.84\.0)"
check "GnuTLS 编译期==运行期 3.8.10" version.out "GnuTLS 3\.8\.10 (3\.8\.10)"
check "SQLite 编译期==运行期 3.49.1" version.out "SQLite 3\.49\.1 (3\.49\.1)"

# 5) ncurses 版本行存在（NCURSES_VERSION 由 ncurses.h 提供）
check "ncurses 版本行存在" version.out "ncurses "

# 6) 可选依赖按预期关闭（未误探测宿主 libmaxminddb/libloc）
check "GeoIP support: no" version.out "GeoIP support: no"

# 7) CLI 帮助可用，且声明了 --version（模式不带前导 '-'，免 grep 误判为选项）
"$NCDC" --help > help.out 2>&1 || { echo "FAIL - ncdc --help 非零退出"; fail=1; }
check "--help 声明 --version" help.out ", --version"

if [ "$fail" -ne 0 ]; then
    echo "ncdc test_package: FAILED"
    exit 1
fi
echo "ncdc test_package: all 7 checks passed"
