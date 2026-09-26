#!/data/service/hnp/bin/bash
# test_package/test.sh — light 1.2.2 消费者断言（HarmonyOS PC）
#
# 诚实性口径：背光读写这一功能面在本平台受 sysfs 权限策略限制（一手 errno 读数见
# ../notes.md），因此这里既不写"功能已验证"，也不写"OHOS 不支持"：
# 只断言能主张的——产物架构、选项文案面、错误路径、以及能力缺失时工具的
# **自行降级**（有诊断、退出码非 0、不被信号杀死）。
#
# rule4 测试账：本文件 PASS 行数 == MANIFEST.yml assertion_count == 日志真实通过数。
set -u

TIMEOUT=/usr/bin/timeout
[ -x "$TIMEOUT" ] || { echo "FAIL: timeout wrapper $TIMEOUT missing or not executable"; exit 1; }
T=$TIMEOUT

# HMDFS 上 hnp bash 在 conan 构建目录里 getcwd 会失败（详见 notes.md），
# 显式 chdir 到已知目录即可恢复；本脚本其余部分只用绝对路径与 PATH 查找。
cd / 2>/dev/null || { echo "FAIL: cannot establish a resolvable working directory"; exit 1; }

pass=0
ok() {
    pass=$((pass + 1))
    echo "PASS $pass: $1"
}
bad() {
    echo "FAIL: $1"
    exit 1
}

# ---- 1. 安装产物可被消费者解析 -------------------------------------------
BINPATH=$(command -v light 2>/dev/null || true)
[ -n "$BINPATH" ] || bad "light not found in conanrun PATH"
[ -f "$BINPATH" ] || bad "light resolved to a non-file: $BINPATH"
ok "installed binary resolvable via conanrun PATH ($BINPATH)"

# ---- 2. ELF 架构真实性（直接读文件头，不依赖 file/readelf）----------------
magic=$(od -An -tx1 -N4 "$BINPATH" | tr -d ' \n')
machine=$(od -An -tx1 -j18 -N2 "$BINPATH" | tr -d ' \n')
[ "$magic" = "7f454c46" ] || bad "not an ELF object (magic=$magic)"
[ "$machine" = "b700" ] || bad "unexpected e_machine, expect b700 (aarch64), got $machine"
ok "ELF magic and e_machine=0xb7 (EM_AARCH64) read back from the installed binary"

# ---- 3. 版本出口：真实执行被测产物 ----------------------------------------
verout=$($T 30 light -V 2>&1); rc=$?
[ "$rc" = "124" ] && bad "light -V timed out"
[ "$rc" = "0" ] || bad "light -V exit=$rc output=$verout"
[ -n "$verout" ] || bad "light -V produced empty output"
ok "light -V 退出码 0 且有输出（实测输出同时含工具自身诊断文案，本条不单独主张版本号）"

# ---- 4. 帮助面：选项文案与上游 usage 一致 ---------------------------------
helpout=$($T 30 light -h 2>&1); rc=$?
[ "$rc" = "124" ] && bad "light -h timed out"
[ "$rc" = "0" ] || bad "light -h exit=$rc"
case "$helpout" in
    *bright*) : ;;
    *) bad "light -h does not document the brightness option surface" ;;
esac
case "$helpout" in
    *-L*) : ;;
    *) bad "light -h does not advertise device listing (-L)" ;;
esac
ok "light -h documents the brightness/-L option surface"

# ---- 5. 无参数调用：必须走错误/用法路径，且不得被信号杀死 ------------------
noargs=$($T 30 light 2>&1); rc=$?
[ "$rc" = "124" ] && bad "bare light invocation timed out"
[ "$rc" -le 128 ] || bad "bare light invocation died by signal (exit=$rc)"
[ -n "$noargs" ] || bad "bare light invocation produced neither usage nor diagnostics"
ok "bare light invocation returns $rc with usage/diagnostics and no signal death"

# ---- 6. 能力面（枚举控制器）：只断言"要么列得出、要么诚实降级"--------------
# 两个分支都算有效行为；静默成功、段错误、非 0 退出但零诊断，一律 FAIL。
enum=$($T 30 light -L 2>&1); rc=$?
[ "$rc" = "124" ] && bad "light -L timed out"
LISTED=$(printf '%s\n' "$enum" | grep -c "/sys/class/")
if [ "$rc" = "0" ] && [ "$LISTED" -gt 0 ]; then
    ok "light -L 实测分支=可枚举：exit 0 且列出 $LISTED 行 /sys/class 目标路径"
elif [ "$rc" = "0" ]; then
    case "$enum" in
        *"No backlight controller"*) ok "light -L 实测分支=诚实降级：exit 0、零个 /sys/class 目标，且工具如实报告无控制器可用（未静默谎报）" ;;
        *) bad "light -L exit 0，既无 /sys/class 目标也无无控制器诊断 ⇒ 静默成功，不可证伪" ;;
    esac
else
    [ "$rc" -le 128 ] || bad "light -L died by signal (exit=$rc)"
    case "$enum" in
        *"failed to open"*|*"Initialization failed"*|*"couldn"*|*"No "*) : ;;
        *) bad "light -L exit=$rc without any diagnostic message" ;;
    esac
    ok "light -L degrades honestly on this platform (rc=$rc, diagnostic emitted, no crash)"
fi

echo "TOTAL: $pass assertions passed"
[ "$pass" = "6" ] || bad "assertion count $pass != declared 6"
exit 0
