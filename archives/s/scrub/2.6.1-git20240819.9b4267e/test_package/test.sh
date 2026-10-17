#!/bin/sh
# scrub test_package —— 真跑包内 scrub 二进制的消费者测试（鸿蒙特有）
# 顶层判定 5 项 = A1–A4 四项断言 + E2E-1 一个完整端到端消费者用例（内含 6 步真判定）
# 被测物：conan runenv PATH 里的 <package>/bin/scrub（self.run(env="conanrun")）
#
# E2E-1 设计依据（全部取自上游文档记载的工作流，不发明用法）：
#   [D1] README.md Examples（L91-L102）与 man/scrub.1.in EXAMPLES（L213-L224）：
#        `scrub <file>` 默认走 NNSA NAP-14.1-C，逐 pass 打印
#        random / random / 0x00 / verify 四行进度                     → E1、E2
#   [D2] man/scrub.1.in SCRUB METHODS（L115-L119）：nnsa = random(x2), 0x00, verify → E2
#   [D3] man/scrub.1.in -r/--remove（L46-L47）"Remove the file after scrubbing."     → E5
#   [D4] man/scrub.1.in -f/--force（L64-L66）"Scrub even if target contains signature
#        indicating it has already been scrubbed."                    → E3、E4、E5
#   [D5] man/scrub.1.in -S/--no-signature（L67-L71）"Do not write scrub signature."  → E6
#   [D6] src/sig.c:28 SCRUB_MAGIC="\001\002\003SCRUBBED!"，writesig 写在文件头部
#        偏移 0（checksig 比对前 12 字节）—— -f/-S 两个选项所指的 "signature" 实体 → E3
# 完整流程：多 pass 擦写 → verify 校验 → 签名落盘 → 二次擦写被拦截 → -f 强制重擦 → -r 删除
set -u
fail=0
e2e_fail=0
TMPWORK="${TMPDIR:-$(pwd)}"
t1="$TMPWORK/scrub-tp-version.$$"
t2="$TMPWORK/scrub-tp-fillff.$$"
t3="$TMPWORK/scrub-tp-dryrun.$$"
t4="$TMPWORK/scrub-tp-default.$$"
t5="$TMPWORK/scrub-tp-e2e.$$"        # E2E-1 主目标（64KiB）
t6="$TMPWORK/scrub-tp-e2enosig.$$"    # E2E-1 E6 对照目标（8KiB）
eout1="$TMPWORK/scrub-tp-e2e-e1.$$.out"   # E1/E2 首次擦写输出
eout4="$TMPWORK/scrub-tp-e2e-e4.$$.out"   # E4 拦截输出
eout5="$TMPWORK/scrub-tp-e2e-e5.$$.out"   # E5 强制重擦+删除输出
eout6a="$TMPWORK/scrub-tp-e2e-e6a.$$.out" # E6 -S 首擦输出
eout6b="$TMPWORK/scrub-tp-e2e-e6b.$$.out" # E6 二次擦写输出
cleanup() {
    rm -f "$t1" "$t2" "$t3" "$t4" "$t5" "$t6" \
          "$eout1" "$eout4" "$eout5" "$eout6a" "$eout6b"
}
trap cleanup EXIT

# A1: --version 自报版本与包版本一致（AC_INIT 字面量 = Conan ref 版本）
v=$(scrub --version 2>&1)
if [ "$v" = "scrub version 2.6.1-git20240819.9b4267e" ]; then
    echo "A1 PASS: --version => $v"
else
    echo "A1 FAIL: --version => '$v'"; fail=1
fi

# A2: fillff 擦写真实文件后逐字节 0xff（核心擦写路径）
dd if=/dev/zero of="$t2" bs=1024 count=64 2>/dev/null || fail=1
scrub -S -p fillff "$t2" >/dev/null 2>&1 || fail=1
nonff=$(od -An -tx1 -v "$t2" | grep -o '[0-9a-f][0-9a-f]' | grep -vc '^ff$')
if [ "$nonff" = "0" ]; then
    echo "A2 PASS: 64KiB 全部字节 0xff"
else
    echo "A2 FAIL: $nonff 个非 0xff 字节"; fail=1
fi

# A3: --dry-run 不落盘（内容保持 0x00 且文件仍存在）
dd if=/dev/zero of="$t3" bs=1024 count=8 2>/dev/null || fail=1
scrub --dry-run -p fillff "$t3" >/dev/null 2>&1 || fail=1
if [ -f "$t3" ] && [ "$(od -An -tx1 -v "$t3" | grep -o '[0-9a-f][0-9a-f]' | grep -vc '^00$')" = "0" ]; then
    echo "A3 PASS: dry-run 未写入且未删除"
else
    echo "A3 FAIL: dry-run 改写了文件或删除了文件"; fail=1
fi

# A4: 默认 pattern（NNSA NAP-14.1-C）+ -r 擦写后 unlink 成功
dd if=/dev/zero of="$t4" bs=1024 count=8 2>/dev/null || fail=1
scrub -r "$t4" >/dev/null 2>&1
if [ ! -e "$t4" ]; then
    echo "A4 PASS: 默认 pattern 擦写后已 unlink"
else
    echo "A4 FAIL: 文件仍存在"; fail=1
fi

# ===== E2E-1: 完整安全擦除端到端消费者用例（6 步，依据见文件头 [D1]-[D6]）=====

# E2E-1/E1: 种子载荷建立 + 默认 NNSA 多 pass 擦写完整跑通（横幅与擦写行非空、rc=0）[D1]
MARKER='SCRUB-E2E-SECRET-20260924-END'
m_len=${#MARKER}
dd if=/dev/zero of="$t5" bs=1024 count=64 2>/dev/null || e2e_fail=1
printf '%s' "$MARKER" | dd of="$t5" bs=1 seek=1024 conv=notrunc 2>/dev/null || e2e_fail=1
seed=$(dd if="$t5" bs=1 skip=1024 count="$m_len" 2>/dev/null)
scrub "$t5" >"$eout1" 2>&1; rc1=$?
if [ "$seed" = "$MARKER" ] && [ "$rc1" = "0" ] && [ -s "$eout1" ] \
   && grep -F -q 'scrub: using NNSA NAP-14.1-C patterns' "$eout1" \
   && grep -F -q "scrub: scrubbing $t5" "$eout1"; then
    echo "E2E-1/E1 PASS: 种子载荷 ${m_len}B 建立 + 默认 NNSA 擦写 rc=0 + 横幅/擦写行非空"
else
    echo "E2E-1/E1 FAIL: seed_len=${#seed} rc=$rc1 out_bytes=$(wc -c <"$eout1" 2>/dev/null)"
    e2e_fail=1
fi

# E2E-1/E2: 四个 pass 行齐全（random×2 / 0x00 / verify），verify 校验 pass 真实执行 [D1][D2]
r=$(grep -c '^scrub: random' "$eout1" 2>/dev/null)
z=$(grep -c '^scrub: 0x00'   "$eout1" 2>/dev/null)
v=$(grep -c '^scrub: verify' "$eout1" 2>/dev/null)
if [ "$r" = "2" ] && [ "$z" = "1" ] && [ "$v" = "1" ]; then
    echo "E2E-1/E2 PASS: pass 行 random=$r 0x00=$z verify=$v（nnsa 四行齐全）"
else
    echo "E2E-1/E2 FAIL: pass 行 random=$r 0x00=$z verify=$v（期望 2/1/1）"
    e2e_fail=1
fi

# E2E-1/E3: 擦写效果字节级校验——载荷区清零（原标记销毁）+ SCRUB_MAGIC 写入文件头 [D4][D6]
z12=$(dd if="$t5" bs=1 skip=1024 count=12 2>/dev/null | od -An -tx1 | grep -c '00 00 00 00 00 00 00 00 00 00 00 00')
m12=$(od -An -tx1 -N12 "$t5" 2>/dev/null | grep -c '01 02 03 53 43 52 55 42 42 45 44 21')
if [ "$z12" = "1" ] && [ "$m12" = "1" ]; then
    echo "E2E-1/E3 PASS: 载荷区 12B 全 0x00（原标记销毁）+ 文件头 SCRUB_MAGIC 12B 逐字节匹配"
else
    echo "E2E-1/E3 FAIL: 载荷区零字节命中=$z12 签名命中=$m12（各期望 1）"
    e2e_fail=1
fi

# E2E-1/E4: 二次擦写被已擦写签名拦截（-f 语义：非零退出 + 官方提示行）[D4]
scrub "$t5" >"$eout4" 2>&1; rc4=$?
if [ "$rc4" = "1" ] && [ -s "$eout4" ] && grep -F -q 'already scrubbed? (-f to force)' "$eout4"; then
    echo "E2E-1/E4 PASS: 二次运行 rc=1 且输出 'already scrubbed? (-f to force)'"
else
    echo "E2E-1/E4 FAIL: rc=$rc4 out_bytes=$(wc -c <"$eout4" 2>/dev/null)"
    e2e_fail=1
fi

# E2E-1/E5: -f 强制重擦 + -r 删除（完整安全擦除流程收口）[D3][D4]
scrub -f -r "$t5" >"$eout5" 2>&1; rc5=$?
if [ "$rc5" = "0" ] && [ -s "$eout5" ] && grep -F -q 'scrub: unlinking' "$eout5" \
   && [ ! -e "$t5" ]; then
    echo "E2E-1/E5 PASS: -f -r 重擦 rc=0 + 'scrub: unlinking' 行 + 文件已删除"
else
    if [ -e "$t5" ]; then t5state=present; else t5state=absent; fi
    echo "E2E-1/E5 FAIL: rc=$rc5 target=$t5state out_bytes=$(wc -c <"$eout5" 2>/dev/null)"
    e2e_fail=1
fi

# E2E-1/E6: -S 不写签名对照——后续擦写不被拦截（与 E4 互为负对照）[D5]
dd if=/dev/zero of="$t6" bs=1024 count=8 2>/dev/null || e2e_fail=1
scrub -S -p fillzero "$t6" >"$eout6a" 2>&1; rc6a=$?
scrub -p fillff "$t6" >"$eout6b" 2>&1; rc6b=$?
if [ "$rc6a" = "0" ] && [ "$rc6b" = "0" ] && [ -s "$eout6b" ] \
   && grep -F -q "scrub: scrubbing $t6" "$eout6b" \
   && ! grep -F -q 'already scrubbed' "$eout6b"; then
    echo "E2E-1/E6 PASS: -S 首擦 rc=0，二次擦写 rc=0 未被签名拦截（负对照成立）"
else
    echo "E2E-1/E6 FAIL: rc6a=$rc6a rc6b=$rc6b out6b_bytes=$(wc -c <"$eout6b" 2>/dev/null)"
    e2e_fail=1
fi

if [ "$e2e_fail" = "0" ]; then
    echo "E2E-1 PASS: 完整安全擦除端到端流程 6/6 步（NNSA 多 pass 擦写→verify 校验→签名落盘→二次擦写拦截→-f 强制重擦+删除→-S 对照）"
else
    echo "E2E-1 FAIL: 端到端流程存在失败步骤"
    fail=1
fi

if [ "$fail" = "0" ]; then
    echo "test_package: 5/5 assertions passed (A1-A4 + E2E-1)"
    exit 0
fi
echo "test_package: FAILURES present"
exit 1
