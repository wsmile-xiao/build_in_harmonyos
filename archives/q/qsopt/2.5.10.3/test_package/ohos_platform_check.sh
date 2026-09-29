#!/bin/sh
# ohos_platform_check.sh — qsopt 鸿蒙特有测试（HarmonyOS 平台适配点验证）
#
# 统一计数口径：独立检查项数（详见 MANIFEST.yml / notes.md）
#   检查 1（H1）：libqsopt_ex.a 目标对象为 AArch64 ELF（OHOS armv8 ABI 适配点）
#   检查 2（H2）：库内无 rpl_malloc/rpl_realloc/rpl_memcmp/rpl_strtod 符号
#                 （OHOS 交叉视角 AC_FUNC 探针 pin 生效，未定义无实现的
#                   rpl_* 宏，否则链接失败——configure/探针 pin 适配点）
#
# 设计依据：这两项直接验证本包在 conanfile.py 中的两个 OHOS 适配点
# （--host=aarch64-unknown-linux-ohos 三元组产物 + 4 个 ac_cv_* 探针 pin），
# 均可在宿主环境对交叉构建产物执行（不运行 OHOS 二进制），本地与 CI 通用。
# 仅使用 POSIX 工具（ar/od/strings），不依赖 PATH 中的解释器/工具链。
#
# 用法: ohos_platform_check.sh <libqsopt_ex.a 绝对路径>
# 退出码: 0=全部通过, 1=任一失败

set -u

LIB="${1:?usage: ohos_platform_check.sh <path-to-libqsopt_ex.a>}"

fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "PASS: $1"; }

[ -f "$LIB" ] || fail "library not found: $LIB"

# ── 检查 1（H1）：AArch64 ELF 目标对象 ──
# 取归档中第一个真实对象成员（跳过 BSD ar 的 __.SYMDEF 与 GNU 的 // 符号表
# 项），解析 ELF header：magic 7f 45 4c 46、EI_CLASS=02（64 位）、
# e_machine=00 b7（183 = EM_AARCH64，小端）。
FIRST_MEMBER=$(ar t "$LIB" 2>/dev/null | grep -vE '^(//|__.SYMDEF)' | head -1)
[ -n "$FIRST_MEMBER" ] || fail "no object member in archive"

ELF_BYTES=$(ar p "$LIB" "$FIRST_MEMBER" 2>/dev/null | od -An -tx1 -N20)
set -- $ELF_BYTES
if [ "${1:-}" = "7f" ] && [ "${2:-}" = "45" ] && [ "${3:-}" = "4c" ] &&
   [ "${4:-}" = "46" ] && [ "${5:-}" = "02" ] &&
   [ "${19:-}" = "b7" ] && [ "${20:-}" = "00" ]; then
    ok "H1: archive member '$FIRST_MEMBER' is ELF64 AArch64 (OHOS armv8 ABI)"
else
    fail "H1: archive member is NOT ELF64 AArch64 (wrong target ABI)"
fi

# ── 检查 2（H2）：无 rpl_* 符号引用 ──
# AC_FUNC 探针 pin 生效时 config.h 不定义 rpl_malloc/rpl_realloc/rpl_memcmp/
# rpl_strtod，对象字符串表中不应出现这些符号名。
if strings "$LIB" 2>/dev/null | grep -qE '^rpl_(malloc|realloc|memcmp|strtod)$'; then
    fail "H2: rpl_* symbols found (AC_FUNC probe pins not effective)"
fi
ok "H2: no rpl_malloc/rpl_realloc/rpl_memcmp/rpl_strtod in library (probe pins effective)"

echo "ALL PASS: ohos_platform_check (2 checks)"
exit 0
