#!/bin/sh
# otpw 1.5 —— 鸿蒙消费者功能测试（test_package/test.sh）
# 用法: test.sh <otpw_bindir>
#
# 上游 1.5 无任何自动化测试（清点见 MANIFEST.yml 与
# reports/upstream-test-scan.txt；Makefile 唯一的 test-login 目标是 ssh 回环
# 手工验证指引），所以下面每一条都是本包新增、真执行打包二进制的断言。
#
# 账本口径：DISCOVERED 只在「发起一条断言」时自加一次，判决一律由
# ok()/bad()/skip() 产出，故恒有 DISCOVERED = PASS + FAIL + SKIP；
# 末尾的自检行会把这条不变式实测出来，不成立即判 FAIL（不许静默）。
#
# 平台纪律：
#   * 鸿蒙 /tmp 只读，toybox sh 的 $(…) 命令替换要往 /tmp 落临时件
#     ⇒ 本脚本**零命令替换、零反引号**；计数一律「重定向到文件 + read」。
#   * 不用 LINES/COLUMNS 作变量名（ash 托管这两个名字）。
#   * 框架 L1e 会对同一 test_package 起第二次 conan test（负向用例）⇒
#     所有产物写进按进程号分址的 $W，两轮不共用。
#
# 行为依据（notes.md 有完整取证）：
#   * `otpw-gen -f <hashfile>` 显式指定哈希文件后跳过 /etc/passwd 查询，
#     因此 uid 无 passwd 条目的主机照样能走完整生成路径；
#   * prefix password 从 stdin 读两行（须一致）；
#   * 熵要求下限 30 bits；-r 与 usage/坏参数路径不碰任何数据库。
#   set -u（非 -e）：多条用例要捕获预期失败的 rc，-e 会中途杀脚本。
set -u

BINDIR="${1:-}"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "test.sh: otpw bindir 未解析（收到 '$BINDIR'）"
    exit 1
fi
GEN="$BINDIR/otpw-gen"
if [ ! -f "$GEN" ]; then
    echo "test.sh: $GEN 不存在 —— 配方没交付 CLI（L1e 破坏性验证期望在此失败）"
    exit 1
fi

BASE="${TMPDIR:-$PWD}"
W="$BASE/otpw-cases.$$"
mkdir -p "$W" || exit 1

PASS=0
FAIL=0
SKIP=0
DISCOVERED=0

ok()   { PASS=$((PASS + 1));   echo "PASS: $1"; }
bad()  { FAIL=$((FAIL + 1));   echo "FAIL: $1"; }
skip() { SKIP=$((SKIP + 1));   echo "SKIP: $1"; }
claim() { DISCOVERED=$((DISCOVERED + 1)); }

# ---------- A. 产物面 ----------
claim
if [ -x "$GEN" ]; then ok "A1 otpw-gen 存在且可执行"; else bad "A1 otpw-gen 存在且可执行"; fi

claim
head -c 4 "$GEN" > "$W/magic" 2>/dev/null
read -r MAGIC < "$W/magic" 2>/dev/null
if grep -q "ELF" "$W/magic" 2>/dev/null; then
    ok "A2 产物是 ELF 镜像"
else
    bad "A2 产物是 ELF 镜像（magic=$MAGIC）"
fi

claim
if [ ! -f "$BINDIR/pam_otpw.so" ] && [ ! -f "$BINDIR/demologin" ]; then
    ok "A3 TARGETS 裁剪生效（包内无 pam_otpw.so / demologin）"
else
    bad "A3 TARGETS 裁剪生效（包内不应有 pam_otpw.so / demologin）"
fi

# ---------- B. usage / 坏参数路径 ----------
claim
"$GEN" -f "$W/b1.hash" -h > "$W/b1.out" 2> "$W/b1.err"
RC_B1=$?
if [ "$RC_B1" = "1" ] && grep -q "One-Time Password Generator v 1.5" "$W/b1.err"; then
    ok "B1 -h 缺参数 → usage 横幅与 rc=1"
else
    bad "B1 -h 缺参数 → usage 横幅与 rc=1（rc=$RC_B1）"
fi

claim
"$GEN" -s 0 > "$W/b2.out" 2> "$W/b2.err"
RC_B2=$?
if [ "$RC_B2" = "1" ] && grep -q "Specify at least 1 page" "$W/b2.err"; then
    ok "B2 -s 0 → 明确报错与 rc=1"
else
    bad "B2 -s 0 → 明确报错与 rc=1（rc=$RC_B2）"
fi

claim
"$GEN" -f "$W/b3.hash" -e 8 > "$W/b3.out" 2> "$W/b3.err"
RC_B3=$?
if [ "$RC_B3" = "1" ] && grep -q "Entropy must be at least 30 bits" "$W/b3.err"; then
    ok "B3 -e 8 → 熵下限 30 bits 报错与 rc=1"
else
    bad "B3 -e 8 → 熵下限 30 bits 报错与 rc=1（rc=$RC_B3）"
fi

claim
"$GEN" -f "$W/b4.hash" -p 99 > "$W/b4.out" 2> "$W/b4.err"
RC_B4=$?
if [ "$RC_B4" = "1" ] && grep -q "One-Time Password Generator v 1.5" "$W/b4.err"; then
    ok "B4 -p 99（未知编码）→ usage 兜底与 rc=1"
else
    bad "B4 -p 99（未知编码）→ usage 兜底与 rc=1（rc=$RC_B4）"
fi

# ---------- C. -r 随机建议路径 ----------
claim
"$GEN" -r > "$W/c1.out" 2> "$W/c1.err"
RC_C1=$?
if [ "$RC_C1" = "0" ]; then ok "C1 -r 退出码 0"; else bad "C1 -r 退出码 0（rc=$RC_C1）"; fi

claim
wc -c < "$W/c1.out" > "$W/c1.size"
read -r C1SIZE < "$W/c1.size"
if [ "$C1SIZE" -gt 0 ] 2>/dev/null; then ok "C2 -r 输出非空（$C1SIZE 字节）"; else bad "C2 -r 输出非空"; fi

claim
read -r W1 W2 DUMMY < "$W/c1.out"
if [ -n "$W1" ] && [ -n "$W2" ] && [ -z "$DUMMY" ]; then
    ok "C3 -r 输出为两段式随机密码（$W1 $W2）"
else
    bad "C3 -r 输出为两段式随机密码"
fi

# ---------- D. 正向生成路径（-f 绕过 passwd 查询 + stdin 喂 prefix password）----------
claim
printf "otpw-test-pw\notpw-test-pw\n" | "$GEN" -f "$W/d.hash" -h 5 -e 30 > "$W/d.list" 2> "$W/d.err"
RC_D1=$?
if [ "$RC_D1" = "0" ]; then ok "D1 端到端生成（-f + stdin 喂密码 + -e 30）rc=0"; else bad "D1 端到端生成 rc=$RC_D1（err 见 $W/d.err）"; fi

claim
grep -q "OTPW list generated" "$W/d.list" && ok "D2 列表含 'OTPW list generated' 页头" || bad "D2 列表缺页头"

claim
grep -q "000 " "$W/d.list" && ok "D3 密码行带三位编号（000 起）" || bad "D3 密码行缺 000 编号"

claim
wc -l < "$W/d.list" > "$W/d.lines"
read -r DLINES < "$W/d.lines"
if [ "$DLINES" = "5" ]; then ok "D4 -h 5 → 列表 5 行（实测 $DLINES）"; else bad "D4 -h 5 → 列表应为 5 行（实测 $DLINES）"; fi

claim
if [ -f "$W/d.hash" ]; then
    wc -c < "$W/d.hash" > "$W/d.hsize"
    read -r DHSIZE < "$W/d.hsize"
    if [ "$DHSIZE" -gt 0 ] 2>/dev/null; then
        ok "D5 哈希文件已写且非空（$DHSIZE 字节）"
    else
        bad "D5 哈希文件为空"
    fi
else
    bad "D5 哈希文件不存在"
fi

claim
printf "otpw-test-pw\notpw-test-pw\n" | "$GEN" -f "$W/d2.hash" -h 5 -e 30 > "$W/d2.list" 2>/dev/null
RC_D6=$?
if [ "$RC_D6" = "0" ] && [ -f "$W/d2.hash" ]; then
    cmp -s "$W/d.hash" "$W/d2.hash"
    CMP_RC=$?
    if [ "$CMP_RC" = "1" ]; then
        ok "D6 两次生成哈希不同（随机源活着，cmp rc=1）"
    else
        bad "D6 两次生成哈希应不同（cmp rc=$CMP_RC）"
    fi
else
    bad "D6 第二次生成失败（rc=$RC_D6）"
fi

claim
printf "otpw-test-pw\notpw-test-pw\n" | "$GEN" -f "$W/d3.hash" -h 5 -e 30 -p 1 > "$W/d3.list" 2> "$W/d3.err"
RC_D7=$?
if [ "$RC_D7" = "0" ] && grep -q "OTPW list generated" "$W/d3.list"; then
    ok "D7 -p 1（英文单词编码）端到端生成 rc=0"
else
    bad "D7 -p 1（英文单词编码）端到端生成（rc=$RC_D7）"
fi

claim
printf "pw-one
pw-two
" | "$GEN" -n -f "$W/d4.hash" -h 5 -e 30 > "$W/d4.list" 2> "$W/d4.err"
RC_D8=$?
if [ "$RC_D8" = "1" ] && grep -q "not identical" "$W/d4.err"; then
    ok "D8 两次 prefix password 不一致 → 'not identical' 与 rc=1（拒绝静默生成）"
else
    bad "D8 两次 prefix password 不一致应报 not identical 且 rc=1（实测 $RC_D8）"
fi

# ---------- E. 行为面补强（-o 顺序模式）----------
claim
printf "otpw-test-pw\notpw-test-pw\n" | "$GEN" -f "$W/e1.hash" -h 5 -e 30 -o > "$W/e1.list" 2>/dev/null
RC_E1=$?
if [ "$RC_E1" = "0" ] && grep -q "000 " "$W/e1.list"; then
    ok "E1 -o（印刷顺序模式）生成 rc=0 且编号行在"
else
    bad "E1 -o（印刷顺序模式）生成（rc=$RC_E1）"
fi

# ---------- 汇总与账本自检 ----------
echo "=== 汇总 discovered=$DISCOVERED pass=$PASS fail=$FAIL skip=$SKIP 合计=$((DISCOVERED)) ==="
if [ "$FAIL" = "0" ]; then PJSON=true; else PJSON=false; fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$PJSON,\"command\":\"/bin/sh test.sh\",\"discovered\":$DISCOVERED,\"passedCount\":$PASS,\"skipped\":$SKIP}"
if [ "$DISCOVERED" != "$((PASS + FAIL + SKIP))" ]; then
    echo "FAIL: 账本不变式破坏 DISCOVERED($DISCOVERED) != PASS($PASS)+FAIL($FAIL)+SKIP($SKIP)"
    exit 1
fi
if [ "$FAIL" != "0" ]; then
    echo "VERDICT: FAIL"
    exit 1
fi
echo "VERDICT: PASS"
exit 0
