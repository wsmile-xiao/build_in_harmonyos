#!/bin/sh
# test_package/test.sh — linuxinfo 4.2.3 消费者功能测试
#
# 设计口径：以"使用者身份"真的执行打包后的 linuxinfo，每条用例都做
# **退出码 + 输出内容**双断言（R34，禁止 print-only 空壳）。
# 上游没有任何自动化测试（MANIFEST.yml 里有逐条清点命令与命中数），
# 所以 linuxinfo 的功能面全部由本脚本承担。
#
# 严格 POSIX sh：OHOS 上只有 /bin/sh(→/system/bin/sh)，没有 /bin/bash。
# 运行环境已由 conan 的 VirtualRunEnv 把包内 bin/ 注入 PATH。

BIN=linuxinfo
fails=0
pass=0

# 计数要在外层 shell 生效，所以不用 subshell 包裹累加
ok() {
    pass=$((pass + 1))
    echo "  [PASS] $1"
}
bad() {
    fails=$((fails + 1))
    echo "  [FAIL] $1"
    [ -n "${2:-}" ] && echo "         detail: $2"
    return 0
}

hdr() { echo "=== $1 ==="; }

# ------------------------------------------------------------------
hdr "TC-00  二进制可定位"
if command -v "$BIN" >/dev/null 2>&1; then
    ok "TC-00.1 '$BIN' 在 PATH 上可执行"
else
    bad "TC-00.1 '$BIN' 不在 PATH 上" "PATH=$PATH"
    echo "FATAL: 被测二进制缺失，后续用例无意义"
    exit 1
fi

# ------------------------------------------------------------------
hdr "TC-01  -v 打印版本（版本号必须与配方版本同源）"
out=$("$BIN" -v 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "TC-01.1 -v 退出码 0" || bad "TC-01.1 -v 退出码" "rc=$rc out=$out"
case "$out" in
    *"4.2.3"*) ok "TC-01.2 -v 输出含上游版本串 4.2.3" ;;
    *)         bad "TC-01.2 -v 输出不含 4.2.3" "out=$out" ;;
esac
case "$out" in
    linuxinfo*) ok "TC-01.3 -v 输出以 argv[0] 'linuxinfo' 开头（argv[0]+VERSION 格式）" ;;
    *)          bad "TC-01.3 -v 输出格式非 '<argv0> <version>'" "out=$out" ;;
esac

# ------------------------------------------------------------------
hdr "TC-02  -h 打印用法行"
out=$("$BIN" -h 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "TC-02.1 -h 退出码 0" || bad "TC-02.1 -h 退出码" "rc=$rc out=$out"
echo "$out" | grep -q -- "print this help" \
    && ok "TC-02.2 -h 含 '-h   print this help' 用法行" \
    || bad "TC-02.2 -h 缺 'print this help' 用法行" "out=$out"
echo "$out" | grep -q -- "print linuxinfo version" \
    && ok "TC-02.3 -h 含 '-v   print linuxinfo version' 用法行" \
    || bad "TC-02.3 -h 缺 'print linuxinfo version' 用法行" "out=$out"

# ------------------------------------------------------------------
hdr "TC-03  喂一个可控 cpuinfo，断言解析结果逐字可预期"
# linuxinfo 允许把 cpuinfo 文件路径作为唯一实参传进去（main(): argc>1 且非
# -v/-h 时 open(argv[1])），这正是本包最实用的可测面。
# 输入按上游 linuxinfo_arm.c 的解析器构造，期望值是从源码逐支推出来的：
#   "Processor" 行            -> processors 1
#   "CPU implementer: 0x41"   -> 查表得 vendor="ARM", processors 2
#   "Type" 行                  -> processors 3   => ordinals[3]="Three"
#   "CPU architecture: 7"     -> model="7"       => "ARM v7 instruction set"
#   "cpu MHz: 528"            -> tempMHz=528     => "528MHz"
#   "BogoMIPS: 1000.50"       -> 上游对 BogoMips/BogoMIPS 各累加一次 => 2001.00
# 注意 /proc/cpuinfo 的键格式必须是 "Key<TAB>: value"：splitstring() 会把冒号前
# 那一个字符抹成 NUL，缺了那个 TAB 就会把键名本身截断。
work_c=$(pwd)/canned-cpuinfo
printf 'Processor\t: ARMv7 Processor rev 5 (v7l)\n' > "$work_c"
printf 'CPU implementer\t: 0x41\n'                  >> "$work_c"
printf 'CPU architecture\t: 7\n'                    >> "$work_c"
printf 'Type\t: ARMv7w\n'                           >> "$work_c"
printf 'cpu MHz\t: 528\n'                           >> "$work_c"
printf 'BogoMIPS\t: 1000.50\n'                      >> "$work_c"

out=$("$BIN" "$work_c" 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "TC-03.1 读 canned cpuinfo 退出码 0" \
                || bad "TC-03.1 退出码非 0" "rc=$rc out=$out"
echo "$out" | grep -qF "Three ARM v7 instruction set" \
    && ok "TC-03.2 厂商/架构解析为 'Three ARM v7 instruction set'" \
    || bad "TC-03.2 CPU 描述不符" "out=$out"
echo "$out" | grep -qF "528MHz" \
    && ok "TC-03.3 频率解析为 '528MHz'" \
    || bad "TC-03.3 频率不符" "out=$out"
echo "$out" | grep -qF "processors, 2001.00 total bogomips" \
    && ok "TC-03.4 复数形态 + bogomips 累加值为 2001.00" \
    || bad "TC-03.4 bogomips/复数形态不符" "out=$out"
lines=$(printf '%s\n' "$out" | grep -c .)
[ "$lines" -ge 3 ] && ok "TC-03.5 输出为 3 段式（OS 行 / CPU 行 / System library 行）" \
                   || bad "TC-03.5 输出段数不足" "lines=$lines out=$out"
rm -f "$work_c"

# ------------------------------------------------------------------
hdr "TC-04  错误路径：不存在的文件要如实报错并返回非 0"
err=$("$BIN" ./definitely-not-a-cpuinfo-$$ 2>&1 >/dev/null); rc=$?
[ "$rc" -ne 0 ] && ok "TC-04.1 不存在的入参 → 非 0 退出码 (got $rc)" \
                || bad "TC-04.1 期望非 0，实际 0" "err=$err"
echo "$err" | grep -q "not found" \
    && ok "TC-04.2 stderr 含 'not found' 报错" \
    || bad "TC-04.2 stderr 缺 'not found'" "err=$err"

# ------------------------------------------------------------------
hdr "TC-05  真机无参运行（OHOS 回归主战场）"
# 上游 GetSystemLibcInfo() 对 gnu_get_libc_version/__libc_version/__linux_C_lib_version
# 三个 .weak 符号做无保护的三选一。OHOS 的 libc 是 musl，实测
#   nm -D /lib/ld-musl-aarch64.so.1 | grep -c <三个符号>  => 0（全符号 1954 个）
# 三个地址都是 0 → 原码走到 else 分支读地址 0 → SIGSEGV(139)。
# patches/0002 补上空指针守卫后应正常退出，并落到它本来就写好的 "Unknown" 默认值。
out=$("$BIN" 2>&1); rc=$?
[ "$rc" -eq 0 ] && ok "TC-05.1 无参读真 /proc/cpuinfo 退出码 0" \
                || bad "TC-05.1 退出码非 0（139=SIGSEGV，说明补丁未生效）" "rc=$rc out=$out"
[ "$rc" -ne 139 ] && ok "TC-05.2 未触发 libc 版本探测空指针崩溃（patches/0002 回归位）" \
                   || bad "TC-05.2 仍然是 SIGSEGV" "out=$out"
echo "$out" | grep -q '^System library ' \
    && ok "TC-05.3 有 'System library ...' 行（musl 下值为 Unknown 属预期）" \
    || bad "TC-05.3 缺 'System library' 行" "out=$out"
# 第一行来自 uname(2)：HarmonyOS 上 sysname 就是 "HarmonyOS"
echo "$out" | head -1 | grep -q "HarmonyOS" \
    && ok "TC-05.4 OS 行首字段取自 uname sysname=HarmonyOS" \
    || bad "TC-05.4 OS 行不含 HarmonyOS" "line1=$(printf '%s\n' "$out" | head -1)"
echo "$out" | grep -q 'RAM' \
    && ok "TC-05.5 内存字段有值（/proc/meminfo 的 MemTotal 可读）" \
    || bad "TC-05.5 无 RAM 字段" "out=$out"

# ------------------------------------------------------------------
hdr "小结"
echo "  PASS=$pass FAIL=$fails"
if [ "$fails" -eq 0 ]; then
    echo "✅ linuxinfo 消费者测试全部通过"
    exit 0
fi
echo "❌ 有 $fails 条断言未通过"
exit 1
