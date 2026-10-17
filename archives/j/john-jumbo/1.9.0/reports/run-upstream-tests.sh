#!/bin/bash
# R51 复现脚本 — john-jumbo 1.9.0 上游 unit-tests（OHOS 真机执行）
#
# 用法（在真机，对 conan 解出的源码树副本）：
#   OPENSSL_INCLUDE=<openssl包include目录> \
#     bash reports/run-upstream-tests.sh <john-source-folder> [cc]
#
# 等价于 src/Makefile.legacy 的 `unit-tests:` 目标 + 三处环境适配（测试逻辑零改动）：
#   1) CPATH 注入 openssl include（目标硬编码 CFLAGS 不用 $(CFLAGS)，sha2.h 含 opensslv.h）
#   2) /tmp/jnk* 临时文件重定向到 cwd（OHOS /tmp 只读 E002；幂等的最小替换）
#   3) 在 <source>/src 下执行（NIST_CAVS 相对数据路径；缺数据文件上游直接 SIGSEGV）
#
# 说明：脚本对传入的源码副本做一次性最小改写（仅 /tmp 路径字符串），请对一次性副本运行。
# 真机实测：37 测试函数 / 43,067,484 次检查全过，退出码 0（见 upstream-test-run.md）。
set -uo pipefail
# 不用 -e：需保留 make 退出码——经 rc 变量输出 [run-upstream-tests] 汇总行后
# 以其退出（同 test.sh 口径）；-e 会在 make 失败时提前中断、丢失 rc 与汇总行。

ROOT=${1:?用法: OPENSSL_INCLUDE=<dir> $0 <john-source-folder> [cc]}
CC=${2:-clang}
: "${OPENSSL_INCLUDE:?请设置 OPENSSL_INCLUDE 指向 openssl 包的 include 目录}"

SRC="${ROOT%/}/src"
if [ ! -f "${SRC}/tests/unit-tests.c" ]; then
    echo "找不到 ${SRC}/tests/unit-tests.c —— 参数应为 john 源码根目录（含 src/）"
    exit 2
fi

# 幂等最小改写：/tmp/jnk* → ./ut-jnk*（仅置换这一处路径字符串；
# 该文件其余引用均为这三个临时文件的建/读/删，逐一对应）
sed 's|/tmp/jnk|./ut-jnk|g' "${SRC}/tests/unit-tests.c" > "${SRC}/tests/unit-tests.c.new"
mv "${SRC}/tests/unit-tests.c.new" "${SRC}/tests/unit-tests.c"

cd "${SRC}"
CPATH="${OPENSSL_INCLUDE}${CPATH:+:${CPATH}}" make -f Makefile.legacy unit-tests CC="${CC}"
rc=$?
echo "[run-upstream-tests] make -f Makefile.legacy unit-tests rc=${rc}"
exit "${rc}"
