#!/data/service/hnp/bin/bash
# test_ohos — lsmount 0.2.4 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 这组用例验证的是「只有把包放到真实鸿蒙 PC 上才能成立」的性质。
# 计数口径（W4 独立审计 r1 纠偏后）：本组 12 条里 **T1..T4b 共 8 条为平台专项**；
# T5a-T5d 这 4 条与 test_package 的 T9a/T9d/T9e/T9f 是同一被测对象、同一数据源、同一判据，
# 在此**只作交叉复核，不并入申报总数** ⇒ 全包不重复断言数 = 28 + 8 = 36。
#
#   T1  产物架构：ELF64 / AArch64（交叉编译目标正确）
#   T2  加固三件套：PIE + GNU_RELRO + BIND_NOW
#       （上游 Makefile 第 8 行把 LDFLAGS 烧成 `-ltermcap -z now`；配方在命令行
#        整体覆盖 LDFLAGS 时把 `-z now` 原样带上，这条断言就是那个覆盖没丢东西的证明）
#   T3  宿主路径不泄漏进产物（构建机 /storage、/home 绝对路径）
#   T4  **鸿特特有无 getpwuid 回归**：本机 euid 不在 /etc/passwd 内，
#       上游 main() 未判空即解引用 pw->pw_dir ⇒ 修复前每次启动必 SIGSEGV(139)。
#       该断言在非鸿蒙 Linux 上恒不成立（那里 getpwuid 通常成功），属平台专有一致性回归。
#   T5  鸿蒙挂载表语义：erofs / hmfs 与 hmmac= 选项是 HarmonyOS 专有，
#       工具必须原样渲染出来
#
# 用法：sh run_ohos_test.sh <已安装 lsmount 二进制路径>
# 退出码：0=全部通过；非 0=有失败（打印首个错误上下文）。
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <binary>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi; }

echo "--- lsmount 0.2.4 HarmonyOS 专项验证 (binary=$BIN) ---"

# T1 架构
readelf -h "$BIN" 2>/dev/null | grep -q "Machine: *AArch64" && r=0 || r=1
chk "T1 产物为 ELF64 AArch64" "$r"
readelf -h "$BIN" 2>/dev/null | grep -q "Class: *ELF64" && r=0 || r=1
chk "T1 产物为 ELF64" "$r"

# T2 加固
readelf -h "$BIN" 2>/dev/null | grep -q "Type: *DYN" && r=0 || r=1
chk "T2a PIE（ET_DYN）" "$r"
readelf -lW "$BIN" 2>/dev/null | grep -q "GNU_RELRO" && r=0 || r=1
chk "T2b GNU_RELRO 段" "$r"
readelf -dW "$BIN" 2>/dev/null | grep -qE "BIND_NOW|FLAGS.*NOW" && r=0 || r=1
chk "T2c BIND_NOW（-z now 生效）" "$r"

# T3 宿主路径泄漏
if strings "$BIN" 2>/dev/null | grep -qE '/storage/Users/|/home/|/tmp/uc2/'; then
    echo "  leak: $(strings "$BIN" | grep -E '/storage/Users/|/home/|/tmp/uc2/' | head -1)"
    chk "T3 无构建机绝对路径泄漏" 1
else
    chk "T3 无构建机绝对路径泄漏" 0
fi

# T4 鸿蒙 uid 无 passwd 条目 → getpwuid 返回 NULL 的崩溃回归
# 注意：toybox 的 /bin/id 解析不了鸿蒙 app uid（实测 `id: bad uid 20020105` 且 stdout 为空），
#       取不到 uid 时必须退回 /proc/self/status，否则下面的 grep 会因空串而**空洞通过**。
uid=$(id -u 2>/dev/null)
if [ -z "$uid" ]; then
    uid=$(awk '/^Uid:/{print $2}' /proc/self/status)
fi
if [ -z "$uid" ]; then
    chk "T4a uid 取不到，本项不可判（拒绝空洞通过）" 1
    chk "T4a-说明 uid 未知，T4b 结论不成立" 1
else
if grep -qE "^[^:]*:[^:]*:${uid}:" /etc/passwd 2>/dev/null; then
    echo "  note: uid=$uid 在 /etc/passwd 中存在，本项不构成平台特有场景"
    chk "T4a (skipped: uid present in passwd)" 0
else
    chk "T4a uid=$uid 不在 /etc/passwd 内（鸿蒙 app uid，平台特有前置条件成立）" 0
fi
"$BIN" --help >/dev/null 2>&1; rc=$?
chk "T4b 无 passwd 条目下启动不再 SIGSEGV（--help rc=$rc，修复前恒为 139）" \
    "$([ "$rc" = 0 ] && echo 0 || echo 1)"
fi

# T5 鸿蒙挂载表语义 —— 与 test_package T9a/T9d/T9e/T9f 同源，**仅作交叉复核，不计入申报总数**
out=$("$BIN" 2>&1); rc=$?
chk "T5a[复核] 默认读取 /proc/mounts 成功 (rc=$rc)" "$([ "$rc" = 0 ] && echo 0 || echo 1)"
printf '%s\n' "$out" | grep -qF "hmfs";  chk "T5b[复核] 渲染出鸿蒙 hmfs" "$?"
printf '%s\n' "$out" | grep -qF "erofs"; chk "T5c[复核] 渲染出鸿蒙 erofs" "$?"
printf '%s\n' "$out" | grep -q  "hmmac="; chk "T5d[复核] 保留鸿蒙 hmmac= 挂载选项" "$?"

echo "--- lsmount 0.2.4 OHOS 专项: $([ "$fail" = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
