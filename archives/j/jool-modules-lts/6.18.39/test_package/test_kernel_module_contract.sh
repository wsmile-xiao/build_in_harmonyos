#!/usr/bin/env bash
# test_kernel_module_contract.sh — jool-modules-lts 6.18.39
# 内核模块源码快照的 fail-closed 契约校验（同 lenovolegionlinux 0.0.20 先例的
# 「内核态交付边界」测试：OHOS 侧无法构建/加载 .ko，但随包交付的内核模块源码
# 必须完整且自洽——缺失任何契约要素即失败，绝不静默通过）。
#
# 断言对象全部来自上游 v4.1.14 源码树的可稽核事实：
#   - src/mod/{nat64,siit}/Makefile 与 src/mod/common/Kbuild 的 obj-m 条目
#   - src/mod/common/init.c 与 nat64/jool.c、siit/jool_siit.c 的
#     MODULE_LICENSE / module_init / module_exit
#   - 三个 Kbuild Makefile 的 /lib/modules 内核树依赖（这正是 OHOS 侧不可构建的根因）
#   - dkms.conf 的 PACKAGE_NAME / BUILT_MODULE_NAME
#   - src/common 共享混合源码（内核态编译时被 #include，必须随快照交付）
#   - 快照不含任何预编译产物
set -u

SNAPSHOT="${1:?usage: test_kernel_module_contract.sh <snapshot_folder>}"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  [ok] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

require_file() { # desc path
    [ -f "$2" ] && ok "$1" || bad "$1（缺失: $2）"
}
require_grep() { # desc pattern file
    grep -Fq -- "$2" "$3" 2>/dev/null && ok "$1" || bad "$1（未命中: '$2' in $3）"
}

echo "== 内核模块源码契约（fail-closed） =="

# 1. 目录与构建文件存在性
require_file "src/mod 存在"                     "$SNAPSHOT/src/mod/common/init.c"
require_file "nat64 Kbuild Makefile 存在"       "$SNAPSHOT/src/mod/nat64/Makefile"
require_file "siit Kbuild Makefile 存在"        "$SNAPSHOT/src/mod/siit/Makefile"
require_file "common Kbuild 存在"               "$SNAPSHOT/src/mod/common/Kbuild"

# 2. Kbuild obj-m 条目（三个内核模块：jool / jool_siit / jool_common）
require_grep "nat64: obj-m += jool.o"           "obj-m += jool.o"        "$SNAPSHOT/src/mod/nat64/Makefile"
require_grep "siit: obj-m += jool_siit.o"       "obj-m += jool_siit.o"   "$SNAPSHOT/src/mod/siit/Makefile"
require_grep "common: obj-m += jool_common.o"   "obj-m += jool_common.o" "$SNAPSHOT/src/mod/common/Kbuild"

# 3. 模块入口与许可证
require_grep "common/init.c: MODULE_LICENSE"    "MODULE_LICENSE"         "$SNAPSHOT/src/mod/common/init.c"
require_grep "common/init.c: module_init"       "module_init"            "$SNAPSHOT/src/mod/common/init.c"
require_grep "common/init.c: module_exit"       "module_exit"            "$SNAPSHOT/src/mod/common/init.c"
require_grep "nat64/jool.c: MODULE_LICENSE"     "MODULE_LICENSE"         "$SNAPSHOT/src/mod/nat64/jool.c"
require_grep "nat64/jool.c: module_init"        "module_init"            "$SNAPSHOT/src/mod/nat64/jool.c"
require_grep "siit/jool_siit.c: MODULE_LICENSE" "MODULE_LICENSE"         "$SNAPSHOT/src/mod/siit/jool_siit.c"
require_grep "siit/jool_siit.c: module_init"    "module_init"            "$SNAPSHOT/src/mod/siit/jool_siit.c"

# 4. 内核树依赖（OHOS 侧不可构建 .ko 的根因证据：KERNEL_DIR ?= /lib/modules/...）
for m in nat64 siit common; do
    require_grep "src/mod/$m: 依赖 /lib/modules 内核树" "/lib/modules" "$SNAPSHOT/src/mod/$m/Makefile"
done

# 5. DKMS 契约
require_file "dkms.conf 存在"                   "$SNAPSHOT/dkms.conf"
require_grep "dkms.conf: PACKAGE_NAME=\"jool\"" "PACKAGE_NAME=\"jool\""  "$SNAPSHOT/dkms.conf"
require_grep "dkms.conf: BUILT_MODULE_NAME"     "BUILT_MODULE_NAME"      "$SNAPSHOT/dkms.conf"

# 6. 内核态编译依赖的共享混合源码（src/common 的 .c 是 header-source hybrids，
#    src/mod 的包装文件会 #include 它们）
for h in xlat.h config.c config.h global.c global.h types.c types.h; do
    require_file "src/common/$h（内核态共享）" "$SNAPSHOT/src/common/$h"
done

# 7. 快照纯净性：不得含任何预编译产物
BAD_COUNT="$(find "$SNAPSHOT/src/mod" \( -name '*.ko' -o -name '*.o' -o -name '*.mod.c' \) 2>/dev/null | wc -l)"
[ "$BAD_COUNT" -eq 0 ] && ok "src/mod 无预编译 .ko/.o/.mod.c" \
    || bad "src/mod 混入 $BAD_COUNT 个预编译产物"

# 8. 上游测试套件随快照交付（平台未来提供内核构建树时可复用）
SH_COUNT="$(find "$SNAPSHOT/test" -name '*.sh' 2>/dev/null | wc -l)"
[ "$SH_COUNT" -eq 36 ] && ok "test/ 36 个上游脚本随快照交付" \
    || bad "test/ 脚本数 $SH_COUNT（期望 36）"
[ -d "$SNAPSHOT/test/unit" ] && ok "test/unit 内核态单元测试随快照交付" \
    || bad "test/unit 缺失"

echo "== test_kernel_module_contract.sh 结果: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
