#!/bin/sh
# ============================================================================
# proda 1.0 — test_package 消费者测试（赛道二硬门禁）
#
# proda 是 package_type="application"：上游**不产出任何库、不装任何头文件**
# （Makefile 只链一个可执行文件 proda），所以"以使用者身份使用这个包"的唯一
# 界面就是**调用被安装进包目录的 proda 二进制**。本脚本因此全部走真实调用：
# 用 fixture 驱动它做真实的概率多序列比对，再用**退出码 + 对输出内容的断言**
# 决定成败（不是"只查文件在不在"，也不是"只打印"）。
#
# 关键的是里面放了 3 组**负向对照**（S4/S5/S13）：
#   -L 999 / 互不相关的序列 / 不存在的文件 时 proda 必须**不**产出比对块。
# 若有人把断言退化成"匹配固定字符串"，负向对照会立刻失守 —— 这三条只有算法
# 真的在 aarch64 上跑起来才成立。
#
# 上游测试：**0 个**（tarball 36 个文件里没有任何测试代码、没有 check 目标、
# 没有测试框架）。取证命令见 notes.md『上游测试清点』。因此本脚本另立
# 31 条消费者断言（14 个场景）作为交付门禁，不拿"上游没测试"当不测的理由。
#
# 依赖环境：由 test_package/conanfile.py 以 `env="conanrun"` 调用，
# proda 已在 PATH 上。可用 PRODA_BIN 覆盖。
# 设备 /tmp 只读 ⇒ 工作目录取 ${TMPDIR:-$PWD}。
# ============================================================================

set -u

PRODA="${PRODA_BIN:-proda}"
WORK="${TMPDIR:-$PWD}/proda-test-$$"
mkdir -p "$WORK" || exit 90
cd "$WORK" || exit 90

SC=0        # 场景计数
A=0         # 断言计数
PASS=0
FAIL=0

sc_start() { SC=$((SC+1)); printf '[%2d/14] %s\n' "$SC" "$1"; }
ok()  { A=$((A+1)); PASS=$((PASS+1)); printf '       PASS A%02d %s\n' "$A" "$1"; }
no()  { A=$((A+1)); FAIL=$((FAIL+1)); printf '       FAIL A%02d %s\n' "$A" "$1"; }

# assert_eq <label> <want> <got>
assert_eq() {
  if [ "$2" = "$3" ]; then ok "$1"; else no "$1 (want=$2 got=$3)"; fi
}
# assert_rc <label> <want> <got>
assert_rc() {
  if [ "$2" = "$3" ]; then ok "$1 (rc=$3)"; else no "$1 (want rc=$2 got rc=$3)"; fi
}
# assert_has <label> <file> <固定串>
assert_has() {
  if grep -q -F -e "$3" "$2" 2>/dev/null; then ok "$1"; else no "$1 (缺少: $3)"; fi
}
# assert_empty <label> <file>
assert_empty() {
  if [ -s "$2" ]; then no "$1 (本应为空，实得 $(wc -l < "$2" | tr -d ' ') 行)"; else ok "$1"; fi
}
# （原 assert_nonempty() 已删：S1-S14 全程未调用它，属死代码。
#   W4 r1 P3。空/非空判定的现行实现是 assert_empty 与就地 [ -s ] 判定。）

# ---------------------------------------------------------------------------
# fixture
# alpha/gamma：同源、尾部 1 个残基不同  -> 必须产出一个比对块
# beta     ：完全无关的序列            -> 不得与 alpha 成块（负向对照用）
# ---------------------------------------------------------------------------
cat > alpha.fa <<'FIXTURE'
>alpha
MKVILLFPVFPLPSVFVLTTSACVATAGMNLCTVSKLIDLGTELATLILEALYNKYQSDFFNMGAIENAYAGQDPSVPDLVNFISTWAGYFDYGGVIPLTNDLLDN
FIXTURE
cat > gamma.fa <<'FIXTURE'
>gamma
MKVILLFPVFPLPSVFVLTTSACVATAGMNLCTVSKLIDLGTELATLILEALYNKYQSDFFNMGAIENAYAGQDPSVPDLVNFISTWAGYFDYGGVIPLTNDLLDQA
FIXTURE
cat > beta.fa <<'FIXTURE'
>beta
MQLQQSTLTLTVKVAGVLLGWVPVAFAKPQVTADGELQNLKGVLPILDWALNQKNTHDATVKVIALFNDPDPKPWVGFYFYFPGVTPVTVYKAGALGGLAGTAFG
FIXTURE

{ cat alpha.fa; cat gamma.fa; } > pair.fa
{ cat alpha.fa; cat beta.fa; } > unrelated.fa
{ cat alpha.fa; cat beta.fa; cat gamma.fa; } > all3.fa

BLOCK="alpha(1-105) gamma(1-105)"   # 实测稳定输出：两端各 1..105 全同源

# ---------------------------------------------------------------------------
sc_start "S1  版本横幅与用法（无参调用）"
"$PRODA" > S1.out 2> S1.err; rc=$?
assert_rc  "proda 无参调用退出码 0" 0 "$rc"
assert_has "stderr 打印上游版本横幅" S1.err "ProDA version 1.0"
assert_has "stderr 打印用法行"      S1.err "Usage: proda [-L length] [-silent] [-posterior] [-tran] [-fasta] filename(s)"

sc_start "S2  默认参数下的真实比对（核心功能）"
"$PRODA" pair.fa > S2.out 2> S2.err; rc=$?
assert_rc  "proda 比对 pair.fa 退出码 0" 0 "$rc"
assert_has "stdout 给出比对块报告"      S2.out "$BLOCK"
# 保守性标注行由 ComputeAnnotation() 逐列算出：同源块必须给 >=60 个 '*'
stars=$(tr -cd '*' < S2.out | wc -c)
if [ $((stars)) -ge 60 ]; then ok "保守性标注行含 >=60 个 *（实得 $((stars)) 个）"; else no "保守性标注行过少（实得 $((stars)) 个）"; fi
assert_has "stderr 报默认最小块长 30"   S2.err "Minimal block length = 30"

sc_start "S3  -L <length> 选项确实生效"
"$PRODA" -L 20 all3.fa > S3.out 2> S3.err; rc=$?
assert_rc  "proda -L 20 退出码 0" 0 "$rc"
assert_has "stderr 报出生效后的最小块长 20" S3.err "Minimal block length = 20"
assert_has "-L 20 下仍产出比对块"           S3.out "$BLOCK"

sc_start "S4  负向对照：-L 999 超过序列长度 => 不得虚报比对块"
"$PRODA" -L 999 all3.fa > S4.out 2> S4.err; rc=$?
assert_rc  "proda -L 999 退出码 0" 0 "$rc"
assert_empty "-L 999 时 stdout 无比对块（阈值真的参与判定）" S4.out

sc_start "S5  负向对照：互不相关的序列不得被配成同源块"
"$PRODA" unrelated.fa > S5.out 2> S5.err; rc=$?
assert_rc  "proda 比对 unrelated.fa 退出码 0" 0 "$rc"
assert_empty "无关序列对不产出比对块（真概率模型在判定，非固定串）" S5.out

sc_start "S6  多文件输入（filename(s) 复数语义）"
"$PRODA" alpha.fa gamma.fa > S6.out 2> S6.err; rc=$?
assert_rc  "proda 接两个独立 fasta 文件退出码 0" 0 "$rc"
assert_has "多文件输入同样产出比对块"           S6.out "$BLOCK"

sc_start "S7  -silent 静默进度"
"$PRODA" -silent pair.fa > S7.out 2> S7.err; rc=$?
assert_rc  "proda -silent 退出码 0" 0 "$rc"
assert_has "-silent 下比对结果仍然完整产出" S7.out "$BLOCK"

sc_start "S8  -posterior 后验概率模式（关掉 Viterbi）"
"$PRODA" -posterior all3.fa > S8.out 2> S8.err; rc=$?
assert_rc  "proda -posterior 退出码 0" 0 "$rc"
# 实测：默认(Viterbi) 给 alpha(1-105) gamma(1-105)，而 -posterior 把同源块
# **多扩出一列**到 1-106（把末尾 N/Q 那个不一致残基按后验概率纳进来，
# 保守性行尾由 '*' 变 ':'）。断言这个更宽的边界，等于同时证明
# -posterior 不是被解析后空转的开关。
assert_has "-posterior 把比对块扩展为 1-106（证明概率模式真的生效）" S8.out "alpha(1-106) gamma(1-106)"

sc_start "S9  -tran 传递性闭包模式"
"$PRODA" -tran all3.fa > S9.out 2> S9.err; rc=$?
assert_rc  "proda -tran 退出码 0" 0 "$rc"
assert_has "-tran 下仍产出比对块"  S9.out "$BLOCK"

sc_start "S10 -fasta 输出模式"
"$PRODA" -fasta all3.fa > S10.out 2> S10.err; rc=$?
assert_rc  "proda -fasta 退出码 0" 0 "$rc"
assert_has "-fasta 下仍产出比对块" S10.out "$BLOCK"

sc_start "S11 未知选项的处理（上游是『忽略并继续』）"
"$PRODA" -zzz pair.fa > S11.out 2> S11.err; rc=$?
assert_rc  "未知选项不致命（退出码 0）"        0 "$rc"
assert_has "stderr 点名被忽略的未知参数"       S11.err "Unknown parameter ignored: -zzz"
assert_has "忽略未知参数后仍完成比对"          S11.out "$BLOCK"

sc_start "S12 -L 带非法值必须报错退出"
"$PRODA" -L abc pair.fa > S12.out 2> S12.err; rc=$?
assert_rc  "-L abc 以退出码 1 终止" 1 "$rc"
assert_has "stderr 给出参数解析错误" S12.err "ERROR: Invalid integer following option -L :: abc"

sc_start "S13 负向对照：不存在的输入文件必须失败"
"$PRODA" no-such-file.fa > S13.out 2> S13.err; rc=$?
# 白名单判定（W4 r1 P3）：只承认"二进制真的跑起来、并按上游语义失败"的退出码。
# 实测 proda 走到 Utilities 的 ASSERT 宏 -> SIGABRT -> rc=134；1/2 是上游 Main 的参数错误退出码。
# 127（找不到二进制）与其它信号一律判 FAIL —— 否则"根本没跑起来"也会被记成 ok。
case "$rc" in
  1|2|134) ok "缺失输入文件以上游真实失败码退出（实测 rc=$rc，属白名单 1/2/134，上游 ASSERT 主动 abort）" ;;
  *) no "缺失输入文件的退出码不在白名单（want rc∈1/2/134 got rc=$rc）" ;;
esac

sc_start "S14 可复现性：同一输入两次运行逐字节一致"
"$PRODA" all3.fa > S14a.out 2>&1
"$PRODA" all3.fa > S14b.out 2>&1
if cmp -s S14a.out S14b.out; then ok "两次运行输出完全相同（无随机化/无时间戳）"; else no "两次运行输出不一致"; fi

# ---------------------------------------------------------------------------
# 自检：脚本自己声明的场景数/断言数必须与账面一致，通过下限由
# test_package/conanfile.py 通过 MIN_PASS 传入（谁声明、谁执法）。
# ---------------------------------------------------------------------------
FLOOR="${MIN_PASS:-0}"
# ---- 账面自检：必须**先于**汇总行完成 -------------------------------------
# W4 r1 P2：原实现把汇总行印在三项自检之前，而自检在其后才把 FAIL 自增，
# 于是场景数/断言数漂移时人读到的是 "SCENARIOS=.. FAIL=0" 的假绿，
# 脚本却以 rc=1 退出 —— 判决文字与退出码相反。
# 现在：自检先跑、汇总行最后印；漂移**不并入 FAIL 计数**（那是断言账），
# 而是额外打印 SELF_CHECK_DRIFT 并以专用退出码 2 终止，
# 使"账面与声明不一致"无法被读成"只是某条断言挂了"，也不再是只加计数不改变退出码。
DRIFT=""
if [ "$SC" -ne 14 ]; then
  echo "SCENARIO_COUNT_MISMATCH want=14 got=$SC"; DRIFT="${DRIFT}SCENARIO "
fi
if [ "$A" -ne 31 ]; then
  echo "ASSERTION_COUNT_MISMATCH want=31 got=$A"; DRIFT="${DRIFT}ASSERTION "
fi
if [ "$PASS" -lt "$FLOOR" ]; then
  echo "BELOW_PASS_FLOOR pass=$PASS floor=$FLOOR"; DRIFT="${DRIFT}FLOOR "
fi
echo "------------------------------------------------------------"
echo "SCENARIOS=$SC ASSERTIONS=$A PASS=$PASS FAIL=$FAIL MIN_PASS=$FLOOR"
rm -rf "$WORK"
[ "$FAIL" -eq 0 ] || exit 1
if [ -n "$DRIFT" ]; then
  echo "SELF_CHECK_DRIFT ${DRIFT}=> rc=2"
  exit 2
fi
exit 0
