#!/bin/sh
# mdm 0.1.3 —— 鸿蒙消费者功能测试（test_package/test.sh）
# 用法: test.sh <mdm_bindir>
#
# 上游 0.1.3 无任何自动化测试（tarball 只有 CHANGES/LICENSE/Makefile/README/
# documents/scripts + include/library/programs 源码，无测试目录、无 check 目标；
# 清点见 MANIFEST.yml 与 reports/upstream-test-scan.txt）。下面每一条都是
# 本包新增、真执行打包二进制的断言。
#
# 交付口径：mdm-run/mdm-master/mdm-slave 三件核心；mdm-top（ncurses 监控器）
# 未构建（见 notes.md「适用边界」）。
#
# 账本口径：DISCOVERED 只在「发起一条断言」时自加一次，判决一律由
# ok()/bad()/skip() 产出，恒有 DISCOVERED = PASS + FAIL + SKIP，末尾自检行
# 实测。平台纪律：零命令替换、零反引号；产物按 pid 分址写 $W；计数 $(( ))。
set -u

BINDIR="${1:-}"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "test.sh: mdm bindir 未解析（收到 '$BINDIR'）"
    exit 1
fi

BASE="${TMPDIR:-$PWD}"
W="$BASE/mdm-cases.$$"
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
for bin in mdm-run mdm-master mdm-slave; do
    claim
    if [ -x "$BINDIR/$bin" ]; then
        ok "A $bin 存在且可执行"
    else
        bad "A $bin 存在且可执行"
    fi
done

claim
head -c 4 "$BINDIR/mdm-run" > "$W/magic" 2>/dev/null
if grep -q "ELF" "$W/magic" 2>/dev/null; then
    ok "A mdm-run 是 ELF 镜像"
else
    bad "A mdm-run 是 ELF 镜像"
fi

claim
if [ ! -f "$BINDIR/mdm-top" ]; then
    ok "A mdm-top 已按交付口径裁剪（包内无 mdm-top）"
else
    bad "A mdm-top 不应出现在包内"
fi

# ---------- B. 功能面（mdm-run 真实 exec 命令）----------
# mdm-run 直通模式说明（programs/mdm-run.c）：无 CMD_SOCK_VAR 环境变量时
# 直接 execvp 下一个参数。被 exec 的程序一律用绝对路径 /bin/sh——conanrun
# 环境的 PATH 不含系统目录，execvp 对绝对路径不做 PATH 查找，环境无关。
claim
"$BINDIR/mdm-run" /bin/sh -c "echo mdm-hello" > "$W/b1.out" 2> "$W/b1.err"
RC_B1=$?
if [ "$RC_B1" = "0" ]; then
    ok "B1 mdm-run 真实 exec 命令（/bin/sh -c）rc=0"
else
    bad "B1 mdm-run 执行失败（rc=$RC_B1，err 见 $W/b1.err）"
fi

claim
grep -q "mdm-hello" "$W/b1.out" && ok "B2 被执行命令的输出透传回 stdout（mdm-hello）" || bad "B2 stdout 未见 mdm-hello（out 见 $W/b1.out）"

claim
"$BINDIR/mdm-run" > "$W/b2.out" 2> "$W/b2.err"
RC_B3=$?
if [ "$RC_B3" != "0" ]; then
    ok "B3 无命令参数 → rc 非 0（拒绝静默空跑，实测 $RC_B3）"
else
    bad "B3 无命令参数应 rc 非 0（实测 0）"
fi

claim
"$BINDIR/mdm-run" /bin/sh -c "exit 3" > "$W/b3.out" 2>/dev/null
RC_B4=$?
if [ "$RC_B4" = "3" ]; then
    ok "B4 子进程退出码透传（exit 3 → mdm-run rc=3）"
else
    bad "B4 子进程退出码透传（应 3，实测 $RC_B4）"
fi

# ---------- 汇总与账本自检 ----------
if [ "$FAIL" = "0" ]; then PJSON=true; else PJSON=false; fi
echo "=== 汇总 discovered=$DISCOVERED pass=$PASS fail=$FAIL skip=$SKIP 合计=$((DISCOVERED)) ==="
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
