#!/bin/sh
# test_package/test_mpop.sh — 消费者行为测试（HarmonyOS PC / ash-toybox 口径）
#
# 用法: sh test_mpop.sh <package_folder> <bin_dir> <scratch_dir> <dep_libdirs>
#
# 立场：以"使用者"身份真的执行打包后的 mpop / mpopd，由断言决定退出码。
# 本设备没有外网 POP3 服务、也没有可连的解析器，所以只覆盖 mpop 主流程里
# **先于任何网络 I/O** 的公开路径（mpop.c:2659 的 net_lib_init() 之前）：
# 版本横幅、usage、选项校验诊断、配置文件解析、--configure 的地址合法性检查。
# 计数写进 <scratch>/checks.count，供 conanfile.py 与申报值双向对账。

set -u

PKG="$1"
BINDIR="$2"
SCRATCH="$3"
LDPATH="$4"

MPOP="$BINDIR/mpop"
MPOPD="$BINDIR/mpopd"
OUT="$SCRATCH/stdout.txt"
ERRF="$SCRATCH/stderr.txt"
COUNT="$SCRATCH/checks.count"

MPOPNAME="mpop"
VERSION="1.4.22"

CHECKS=0
FAILS=0

report() { printf 'ok   %s\n' "$1"; CHECKS=$((CHECKS + 1)); }
die() {
    printf 'FAIL %s\n' "$1" >&2
    printf '%s\n' "$CHECKS" > "$COUNT"
    exit 1
}

# 每一次真实执行都带超时守卫；没有 timeout(1) 就明确失败，绝不静默降级。
TIMEOUT=""
for c in /system/bin/timeout /data/service/hnp/bin/timeout /usr/bin/timeout /bin/timeout; do
    if [ -x "$c" ]; then TIMEOUT="$c"; break; fi
done
if [ -z "$TIMEOUT" ]; then
    if command -v timeout >/dev/null 2>&1; then
        TIMEOUT="$(command -v timeout)"
    fi
fi
if [ -z "$TIMEOUT" ] || [ ! -x "$TIMEOUT" ]; then
    printf 'FAIL no executable timeout(1) found; every run must be time-guarded\n' >&2
    printf '0\n' > "$COUNT"
    exit 1
fi

# 打包产物无 RPATH/RUNPATH，运行期库搜索路径由 Conan 的 conanrun 环境给出；
# 这里再显式补一次依赖闭包目录，保证脚本单独手工执行时也能跑。
LD_LIBRARY_PATH="$LDPATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
export HOME="$SCRATCH"
export LC_ALL=C

# run <args...> ：结果留在 $? / $OUT / $ERRF
run() {
    "$TIMEOUT" 60 "$@" >"$OUT" 2>"$ERRF"
}

# 断言辅助
expect_rc()    { [ "$1" -eq "$2" ] || die "$3 (rc=$1, want $2; stderr: $(head -c 200 "$ERRF" | tr '\n' ' '))"; }
# -e 是必需的：断言模式里有以 '-' 开头的字面量（如 --all-accounts），
# 不锁 -e 的话 grep 会把模式当成自己的选项。
expect_has()   { grep -q -e "$2" "$1" || die "$3 (pattern '$2' absent from $( [ "$1" = "$OUT" ] && echo stdout || echo stderr ))"; }
expect_absent() {
    if grep -q -e "$2" "$1"; then
        die "$3 (pattern '$2' must not appear)"
    fi
}

printf '# mpop %s consumer test (ash/toybox)\n' "$VERSION"

# ── 1. 两个交付的可执行程序都在包里，且是可执行常规文件 ────────────────────
[ -f "$MPOP" ]  || die "packaged mpop is missing under $BINDIR"
[ -x "$MPOP" ]  || die "packaged mpop is not executable"
[ -f "$MPOPD" ] || die "packaged mpopd is missing under $BINDIR"
[ -x "$MPOPD" ] || die "packaged mpopd is not executable"
report "bin/mpop 与 bin/mpopd 均已打包且可执行"

# ── 2..7 mpop --version：真执行，且断言的是编译期常量（证明依赖选择生效）──
run "$MPOP" --version
expect_rc "$?" 0 "mpop --version must exit 0"
expect_has "$OUT" "^$MPOPNAME version $VERSION\$" \
    "mpop --version must print the autoconf-substituted version"
report "mpop --version 退出码 0 且打印 '$MPOPNAME version $VERSION'（config.status 替换生效）"

PLATFORM_LINE="$(grep '^Platform: ' "$OUT" || true)"
if [ -z "$PLATFORM_LINE" ]; then die "mpop --version prints no Platform: line"; fi
printf '%s\n' "$PLATFORM_LINE" > "$SCRATCH/platform.txt"
# PLATFORM 是 configure 用 AC_CANONICAL_TARGET 探测后写进 config.h 的三元组。
# E007 的 config.guess 补丁规定输出 aarch64-unknown-linux-ohos ⇒ 必须同时含
# aarch64 与 ohos（"unknown" 是三元组的 vendor 字段，不是探测失败的标志）。
expect_has "$SCRATCH/platform.txt" "aarch64" \
    "mpop --version Platform line must carry the AArch64 architecture"
expect_has "$SCRATCH/platform.txt" "ohos" \
    "mpop --version Platform line must carry the OHOS kernel field (E007)"
report "mpop --version 的 Platform 行取到真实 OHOS target 三元组: $PLATFORM_LINE"

expect_has "$OUT" "TLS/SSL library: GnuTLS" \
    "mpop --version must report GnuTLS (the --with-tls=gnutls choice)"
report "mpop 链接的是 GnuTLS 后端（--with-tls=gnutls 实测生效）"

expect_has "$OUT" "Authentication library: built-in" \
    "mpop must report the built-in SASL set, i.e. HAVE_LIBGSASL is off"
expect_absent "$OUT" "GNU SASL" \
    "libgsasl must not be reported as present"
report "认证库报为 built-in（制品仓无 libgsasl>=2.1 ⇒ 关闭后的真实后果）"

expect_has "$OUT" "IDN support: enabled" \
    "mpop must report IDN as enabled (libidn2 is a declared dependency)"
report "IDN support: enabled（libidn2 被真实链接）"

# ── 8..11 mpop --help ──────────────────────────────────────────────────────
run "$MPOP" --help
expect_rc "$?" 0 "mpop --help must exit 0"
expect_has "$OUT" "Mail retrieval mode (default):" \
    "mpop --help must print the mail-retrieval usage block"
report "mpop --help 退出码 0 并打印取信模式用法"
expect_has "$OUT" "--all-accounts" "mpop --help must document --all-accounts"
expect_has "$OUT" "Report bugs to <marlam@marlam.de>" \
    "mpop --help must carry the upstream bug address"
report "mpop --help 列出 --all-accounts 与上游 bug 地址"

# ── 12..16 选项校验（发生在任何网络动作之前）──────────────────────────────
run "$MPOP" --definitely-not-an-option
expect_rc "$?" 64 "an unknown option must exit EX_USAGE(64)"
report "未知长选项退出码 EX_USAGE=64（getopt 分支）"

run "$MPOP" --port=0
RC=$?
expect_has "$ERRF" "invalid argument 0 for --port" \
    "mpop must reject --port=0 with the upstream diagnostic"
expect_rc "$RC" 64 "mpop --port=0 must exit EX_USAGE(64)"
report "--port=0 被拒并打印 'invalid argument 0 for --port'，退出码 64"

run "$MPOP" --pipelining=bogus
RC=$?
expect_has "$ERRF" "invalid argument bogus for --pipelining" \
    "mpop must reject --pipelining=bogus"
expect_rc "$RC" 64 "mpop --pipelining=bogus must exit EX_USAGE(64)"
report "--pipelining=bogus 被拒（退出码 64 + 诊断）"

run "$MPOP" --received-header=bogus
RC=$?
expect_has "$ERRF" "invalid argument bogus for --received-header" \
    "mpop must reject --received-header=bogus"
expect_rc "$RC" 64 "mpop --received-header=bogus must exit EX_USAGE(64)"
report "--received-header=bogus 被拒（退出码 64 + 诊断）"

run "$MPOP" --host=pop.example.com --all-accounts
RC=$?
expect_has "$ERRF" "cannot use both --host and accounts" \
    "mpop must reject --host together with --all-accounts"
expect_rc "$RC" 64 "--host + --all-accounts must exit EX_USAGE(64)"
report "--host 与 --all-accounts 互斥（退出码 64 + 诊断）"

run "$MPOP" --all-accounts someaccount
RC=$?
expect_has "$ERRF" "cannot use both --all-accounts and a list of accounts" \
    "mpop must reject --all-accounts with an account list"
expect_rc "$RC" 64 "--all-accounts + account list must exit EX_USAGE(64)"
report "--all-accounts 与账户列表互斥（退出码 64 + 诊断）"

# ── 17..19 配置文件解析（get_conf 失败即 goto exit，网络栈尚未初始化）──────
MISSING="$SCRATCH/no-such-mpoprc"
run "$MPOP" -C "$MISSING" --all-accounts
RC=$?
expect_rc "$RC" 74 "an unreadable config file must exit EX_IOERR(74)"
expect_has "$ERRF" "$MISSING" "the diagnostic must name the config file"
report "-C 指向不存在的配置文件 ⇒ 退出码 EX_IOERR=74 且诊断点名该文件"

printf 'account\n' > "$SCRATCH/bad-syntax.rc"
run "$MPOP" -C "$SCRATCH/bad-syntax.rc" --all-accounts
RC=$?
expect_rc "$RC" 78 "a syntactically broken config must exit EX_CONFIG(78)"
expect_has "$ERRF" "missing account name" \
    "mpop must report the upstream 'missing account name' parse error"
report "坏配置文件（裸 account 关键字）⇒ EX_CONFIG=78 + 'missing account name'"

printf '# no accounts at all\n' > "$SCRATCH/empty.rc"
run "$MPOP" -C "$SCRATCH/empty.rc" --all-accounts
RC=$?
expect_rc "$RC" 78 "a config without accounts must exit EX_CONFIG(78)"
expect_has "$ERRF" "no accounts defined" \
    "mpop must report 'no accounts defined'"
report "无账户的配置文件 ⇒ EX_CONFIG=78 + 'no accounts defined'"

# ── 20 --configure 的地址合法性（早于任何 SRV/DNS 查询）────────────────────
run "$MPOP" --configure=nobody-without-at-sign
RC=$?
expect_rc "$RC" 65 "an invalid address must exit EX_DATAERR(65)"
expect_has "$ERRF" "invalid mail address" \
    "mpop_configure must reject a local-part-only address before any DNS work"
report "--configure 对非法地址返回 EX_DATAERR=65（该分支在任何 SRV 查询之前）"

# ── 21..23 mpopd：第二个交付程序，同样离线可跑 ─────────────────────────────
run "$MPOPD" --version
expect_rc "$?" 0 "mpopd --version must exit 0"
expect_has "$OUT" "^mpopd version $VERSION\$" \
    "mpopd --version must print the substituted version"
report "mpopd --version 退出码 0 且打印 'mpopd version 1.4.22'"

run "$MPOPD" --help
expect_rc "$?" 0 "mpopd --help must exit 0"
expect_has "$OUT" "Usage: mpopd \[option" "mpopd --help must print its usage line"
expect_has "$OUT" "--maildir=dir" "mpopd --help must document --maildir"
report "mpopd --help 退出码 0 并打印 usage 与 --maildir 选项"

run "$MPOPD"
RC=$?
if [ "$RC" -eq 0 ]; then die "mpopd without --auth/--maildir must not report success"; fi
expect_has "$ERRF" "missing --auth and --maildir option" \
    "mpopd must state the missing mandatory option pair"
report "mpopd 缺少 --auth/--maildir 时非零退出并给出诊断（未触网）"

# ── 24 负对照：去掉依赖闭包搜索路径后必须被加载器拒载（R34 反证）───────────
run env LD_LIBRARY_PATH="$SCRATCH/empty-libdir" "$MPOP" --version
RC=$?
if [ "$RC" -eq 0 ]; then
    die "mpop ran without the dependency libdirs; the test would not prove the package is consumed"
fi
expect_has "$ERRF" "Error loading shared library" \
    "the refusal must come from the runtime loader, not from mpop itself"
report "去掉 Conan 运行库路径后 mpop 被加载器拒载 ⇒ 被测二进制确实消费本包依赖闭包"

printf '%s\n' "$CHECKS" > "$COUNT"
printf 'mpop consumer behaviour checks: %s checks passed\n' "$CHECKS"
exit 0
