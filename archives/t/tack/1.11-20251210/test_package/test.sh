#!/bin/sh
# tack 1.11-20251210 —— 消费者行为测试源文件
#
# 由 test_package/conanfile.py 的 test() 用 self.run(..., env="conanrun") 真实调用；
# 入参：$1 = 被测二进制路径，$2 = 包根目录，$3 = 该二进制是否已被 test() 自签（1/0）。
# 任一检查点不成立即 exit 1（不吞失败）。
#
# 上游测试面口径（详见 test_package/MANIFEST.yml）：tack 1.11-20251210 **没有自动化
# 自测**——Makefile.in 的 `check:` 目标体是 `@echo "** no self-test available"`，
# 四类测试资产（test* 框架源码 / */res 语料 / *RUNTEST*.sh / demo|examples 的 .c）
# 实测命中数全为 0。⇒ 本文件的 21 个检查点全部是"执行打包产物、由退出码与输出判定"
# 的行为断言，另加对产物的平台一致性静态检查；没有一条写成恒真。
#
# 交互式主循环（tack 的真实用途：探测终端并重建 terminfo 条目）在无头构建主机上
# **不可运行**：实测 `timeout 20 tack vt100 < /dev/null` 不退出、单核 ~98% 空转，
# 由 timeout 判 rc=124。该路径按 skipped 逐条记录在 MANIFEST.yml 与 notes.md，
# 不记为通过。
set -u

BIN="$1"
PKG="$2"
SIGNED="$3"
MAN="$PKG/share/man/man1/tack.1"

total=0
pass=0

# gate <0=条件成立|非0=不成立> <编号> <说明>
gate() {
    total=$((total + 1))
    if [ "$1" -eq 0 ]; then
        pass=$((pass + 1))
        echo "ok $2 - $3"
    else
        echo "FAIL $2 - $3"
        exit 1
    fi
}

# tack 会在工作目录落盘（-d -> debug.log、-l -> tack.log），所以一切都在临时目录里跑，
# 绝不在归档树/测试包目录里留文件。
WORK="${TMPDIR:-$HOME/tmp}/tack-consumer-$$"
mkdir -p "$WORK" || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM HUP
cd "$WORK" || exit 1

RE=""
for cand in llvm-readelf readelf /data/service/hnp/bin/llvm-readelf; do
    if command -v "$cand" > /dev/null 2>&1; then
        RE="$cand"
        break
    fi
done
if [ -z "$RE" ]; then
    echo "FAIL A0 - 没有可用的 readelf，静态断言无法执行"
    exit 1
fi

# ---- A：--version 路径（与终端无关的完整代码路径）------------------------------
"$BIN" -V > v.out 2> v.err
rc=$?
gate $([ "$rc" -eq 1 ] && echo 0 || echo 1) A1 "-V 退出码=1（上游 tack.c：print_version 后 ExitProgram(EXIT_FAILURE)，非本窗改动）"
gate $(grep -q 'tack version 1.11 (20251210)' v.out && echo 0 || echo 1) A2 "-V 打印版本串 1.11 (20251210)"
gate $(grep -q 'License version 2' v.out && echo 0 || echo 1) A3 "-V 打印 GPL-2 授权声明"

# ---- B：非法选项路径（usage 走 stderr，上游退出码是 0）--------------------------
env -u TERM "$BIN" -q > q.out 2> q.err
rc=$?
gate $([ "$rc" -eq 0 ] && echo 0 || echo 1) B1 "非法选项 -q 退出码=0（上游 main() default 分支 ExitProgram(EXIT_SUCCESS)）"
gate $(grep -q 'usage: ' q.err && echo 0 || echo 1) B2 "非法选项把 usage 打到 stderr"

# ---- C：TERM 缺失（validate_term 前置校验，不触碰终端）--------------------------
env -u TERM "$BIN" > c.out 2> c.err
rc=$?
gate $([ "$rc" -eq 1 ] && echo 0 || echo 1) C1 "无 \$TERM 且无参数时退出码=1"
gate $(grep -q 'no useful value found for' c.err && echo 0 || echo 1) C2 "无 \$TERM 时报 'no useful value found for \$TERM'"

# ---- D：参数过多（curses_setup 之前的另一条确定性分支）-------------------------
env -u TERM "$BIN" vt100 xterm > d.out 2> d.err
rc=$?
gate $([ "$rc" -eq 1 ] && echo 0 || echo 1) D1 "两个位置参数时退出码=1"
gate $(grep -q 'usage: ' d.err && echo 0 || echo 1) D2 "两个位置参数时打印 usage"

# ---- E：terminfo 数据库可达性（证明 conan runenv 的 TERMINFO 生效）--------------
env TERM=tack-no-such-term-zz9 "$BIN" > e.out 2> e.err
rc=$?
gate $([ "$rc" -eq 1 ] && echo 0 || echo 1) E1 "未知终端名时退出码=1"
gate $(grep -q 'listed as generic' e.err && echo 0 || echo 1) E2 "未知终端名报 '... listed as generic'：setupterm 真读到了 ncurses 包里的 terminfo 库（TERMINFO 未注入时会改报 'database could not be found'）"

# ---- F：鸿蒙特有——ELF 结构 ------------------------------------------------------
"$RE" -h "$BIN" > h.out 2> h.err
gate $(grep -q 'Machine: *AArch64' h.out && echo 0 || echo 1) F1 "ELF Machine = AArch64"
"$RE" -d "$BIN" > d.out 2> d2.err
gate $(grep NEEDED d.out | grep -q 'ncursesw' && echo 1 || echo 0) F2 "DT_NEEDED 不含 ncursesw => 链进的是 conan 静态归档，不是宿主 harmonybrew/system 的同名 libncursesw.so.6"
gate $(grep NEEDED d.out | grep -q 'libc\.so' && echo 0 || echo 1) F3 "DT_NEEDED 含 libc.so（产物确为可执行 ELF，不是半截目标文件）"
gate $(grep NEEDED d.out | grep -q '/' && echo 1 || echo 0) F4 "所有 DT_NEEDED 条目都是裸 soname（不含 '/'；绝对路径 NEEDED 会被 OHOS 加载器拒载）"
"$RE" -l "$BIN" > l.out 2> l.err
gate $(grep -q 'program interpreter: /lib/ld-musl-aarch64.so.1' l.out && echo 0 || echo 1) F5 "程序解释器 = /lib/ld-musl-aarch64.so.1（OHOS musl 目标，不是 glibc）"
"$RE" -S "$BIN" > s.out 2> s.err
secs=$(grep -c '[.]codesign' s.out)
if [ "$SIGNED" = "1" ]; then
    gate $([ "$secs" -eq 1 ] && echo 0 || echo 1) F6 "OHOS 分支：test() 已在归档树外自签，被测 ELF 的 .codesign 段实测=1（实测值：$secs）"
else
    gate $([ "$secs" -eq 0 ] && echo 0 || echo 1) F6 "非 OHOS 分支：未经自签的 ELF 不该带 .codesign 段（实测值：$secs）"
fi

# ---- G：鸿蒙特有——宿主前缀/宿主路径泄漏 ----------------------------------------
hb=$(grep -a -c 'harmonybrew' "$BIN" || true)
gate $([ "${hb:-1}" -eq 0 ] && echo 0 || echo 1) G1 "包内二进制字节里 harmonybrew 路径计数=0（实测值：$hb）"
ul=$(cat "$BIN" "$MAN" 2> /dev/null | grep -a -c '/usr/local' || true)
gate $([ "${ul:-1}" -eq 0 ] && echo 0 || echo 1) G2 "二进制 + man 页里 /usr/local 宿主前缀计数=0（实测值：$ul）"

# ---- H：交付面（commands.json 的双向集合差以此为准）-----------------------------
nbin=$(ls "$PKG/bin" | wc -l)
gate $([ "$nbin" -eq 1 ] && echo 0 || echo 1) H1 "包内 bin/ 实测恰好 1 个条目（实测值：$nbin）"
gate $([ -s "$MAN" ] && echo 0 || echo 1) H2 "share/man/man1/tack.1 存在且非空"

echo "consumer assertions passed: $pass/$total"
[ "$pass" -eq "$total" ] || exit 1
exit 0
