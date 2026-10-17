#!/bin/sh
# test_sash.sh — sash 3.8 test_package 消费者测试（真执行断言，R34/R51）
#
# 用法: sh test_sash.sh <bin_dir>
# 退出码: 0 = 全部断言通过；非 0 = 有断言失败（不吞退出码）
#
# 上游 sash 3.8 不含任何测试套件（清点证据见同目录 MANIFEST.yml），故本脚本
# 是本包唯一的执行级验证，逐条真跑 sash 二进制。
#
# 断言选取口径：sash 的大量内建命令是特权操作（-mount/-umount/-chroot/
# -pivot_root/-losetup/-mknod/-kill），在 HarmonyOS PC 沙箱（非 root、无
# CAP_SYS_ADMIN）必然受限；本脚本**全部选择不依赖特权的代码路径** —— 命令行
# 参数解析、usage()、内建命令表分派、以及穿过 zlib 的 -gzip / -gunzip 往返。
# 因此每条断言的成败只反映包本身，不反映环境权限。
#
# 所有中间文件只写在脚本自建的临时子目录内，并在退出前删除，避免把测试副
# 产物留在包目录里。
set -u  # 不套 set -e：每条断言自行判定成败并汇总计数，需全部跑完再统一给退出码

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi

BIN_DIR="$1"
SASH="$BIN_DIR/sash"
PASS=0
FAIL=0
TOP=$(pwd)
TMPW="$TOP/sash-test-tmp"

ok()  { PASS=$((PASS + 1)); echo "  OK   $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  FAIL $1" >&2; }

cleanup() { [ -n "$TMPW" ] && rm -rf "$TMPW" 2>/dev/null; }
trap cleanup EXIT

echo "===== sash 3.8 消费者测试 ====="

# --- A1a: 产物存在且带可执行位 -------------------------------------------
echo "-- A1 产物存在性与可执行性"
if [ -x "$SASH" ]; then
    ok "A1a bin/sash 存在且带可执行位"
else
    bad "A1a bin/sash 不存在或无执行位: $SASH"
    echo "后续断言无法执行" >&2
    exit 1
fi

# --- A1b: 内核真的允许加载执行（.codesign 有效性冒烟门） ------------------
# 鸿蒙内核对 ELF 的 .codesign 段做加载期校验：签名失效的二进制即使执行位
# 正确也会以 EPERM（shell rc=126）被拒绝，且与 chmod 无关。若没有这道门，
# 后面所有断言都会拿 rc=126 当作"命令失败/不存在"而假性通过 —— 本包首次
# W3 失败正是以这种方式暴露了 A7 的假阳性。
SMOKE=$("$SASH" -c '-echo sash-smoke' 2>&1)
SMOKE_RC=$?
if [ "$SMOKE_RC" -eq 0 ] && [ "$SMOKE" = "sash-smoke" ]; then
    ok "A1b sash 可被内核加载执行（.codesign 有效），冒烟回显正确"
else
    bad "A1b sash 无法执行 (rc=$SMOKE_RC out=[$SMOKE]) —— 后续断言全部作废，拒绝假性通过" >&2
    echo "===== 汇总: PASS=$PASS FAIL=$((FAIL + 1)) =====" >&2
    exit 1
fi

# --- A2: 版本串（走 usage() 真实代码路径，非特权） -----------------------
# sash.c 的 usage() 向 stderr 打印 "Stand-alone shell (version %s)" 并 exit(1)
echo "-- A2 版本串 / 参数解析"
A2OUT=$("$SASH" -h 2>&1)
A2RC=$?
if echo "$A2OUT" | grep -q 'Stand-alone shell (version 3\.8)'; then
    ok "A2a usage() 输出含上游版本串 3.8"
else
    bad "A2a 版本串缺失，实际输出: $A2OUT"
fi
if [ "$A2RC" -eq 1 ]; then
    ok "A2b sash -h 按上游语义以退出码 1 结束（证明进程正常跑完而非崩溃）"
else
    bad "A2b sash -h 退出码应为 1，实为 $A2RC"
fi

# --- A3: 内建命令表分派 ---------------------------------------------------
# -echo 是内建命令；名字带前导 '-' 使其不可能命中任何外部可执行文件，
# 因此成功只可能来自包内实现。
echo "-- A3 内建命令分派"
A3OUT=$("$SASH" -c '-echo sash-ok-3-8' 2>&1)
A3RC=$?
if [ "$A3RC" -eq 0 ] && [ "$A3OUT" = "sash-ok-3-8" ]; then
    ok "A3 sash -c '-echo ...' 精确回显，内建命令分派可用"
else
    bad "A3 -echo 异常 (rc=$A3RC out=[$A3OUT])"
fi

# --- A4~A6: zlib 压缩/解压往返（实质依赖本包唯一外部依赖） ---------------
# -gzip 无 -o 时压缩为 <name>.gz 并**删除原文件**（cmd_gzip.c 的
# outPath == NULL 分支 + unlink），-gunzip 反之去掉 .gz；因此往返天然不会
# 撞上"不能压缩到自己身上"的检查。
echo "-- A4~A6 zlib 压缩/解压往返（真执行 zlib 的 gzopen/gzwrite/gzread）"
mkdir -p "$TMPW" || { bad "A4~A6 无法建立临时目录 $TMPW"; TMPW=""; }
if [ -n "$TMPW" ]; then
    cd "$TMPW" || exit 1
    # 用高度可重复的内容，保证 .gz 严格小于原文
    i=0
    : > ref.txt
    while [ "$i" -lt 200 ]; do
        echo "sash zlib roundtrip payload line $i aaaaaaaaaaaaaaaaaaaaaaaa" >> ref.txt
        i=$((i + 1))
    done
    cp ref.txt src.txt
    SZ0=$(wc -c < src.txt | tr -d ' ')

    # A4: 压缩产出 .gz
    if "$SASH" -c '-gzip src.txt' > gz.log 2>&1 && [ -f src.txt.gz ]; then
        ok "A4 -gzip 退出 0 且产出 src.txt.gz"
    else
        bad "A4 -gzip 失败: $(cat gz.log 2>/dev/null)"
    fi

    # A5: 产物确实变小（证明 deflate 真在干活，而不是原样拷字节）
    if [ -f src.txt.gz ]; then
        SZ1=$(wc -c < src.txt.gz | tr -d ' ')
        if [ "$SZ1" -lt "$SZ0" ]; then
            ok "A5 src.txt.gz ($SZ1) 小于原文 ($SZ0)，zlib deflate 生效"
        else
            bad "A5 压缩产物未变小: $SZ1 >= $SZ0"
        fi
    else
        bad "A5 无 src.txt.gz 可比对"
    fi

    # A6: 解压回来与参照逐字节相同（证明 inflate 路径 + 链入的 libz.a 正确）
    if "$SASH" -c '-gunzip src.txt.gz' > un.log 2>&1 && cmp -s src.txt ref.txt; then
        ok "A6 -gunzip 还原后与参照逐字节相同（zlib inflate 路径可用）"
    else
        bad "A6 往返不一致: $(cat un.log 2>/dev/null)"
    fi

    # A8: 文件列举内建命令（非特权，同样在临时目录内完成）
    if "$SASH" -c '-ls .' > ls.log 2>&1 && grep -q 'ref.txt' ls.log; then
        ok "A8 sash -c '-ls .' 列出目录内容，文件类内建命令可用"
    else
        bad "A8 -ls 异常: $(cat ls.log 2>/dev/null)"
    fi

    cd "$TOP" || exit 1
fi

# --- A7: 功能面裁剪的可观测断言（HAVE_LINUX_ATTR=0 的既证结果） ----------
# -lsattr / -chattr 的编译开关已关；命令名前导 '-' 使其不可能命中任何外部
# 可执行文件，故 sash 会落到 execvp 并 perror 报 "No such file or directory"
# 后返回非 0。这里**同时要求失败形态匹配**，不接受 rc=126 之类的执行层失败
# 冒充裁剪成功。
echo "-- A7 功能面裁剪断言（-chattr/-lsattr 已按上游开关关闭）"
LA="$TOP/.sash-la.log"
"$SASH" -c '-lsattr .' > "$LA" 2>&1
LARC=$?
if [ "$LARC" -ne 0 ] && grep -q 'lsattr: No such file' "$LA" 2>/dev/null; then
    ok "A7 -lsattr 未编入（execvp 报 No such file，rc=$LARC），与 HAVE_LINUX_ATTR=0 的裁剪一致"
else
    bad "A7 -lsattr 失败形态与裁剪声明不符 (rc=$LARC): $(cat "$LA" 2>/dev/null)"
fi
rm -f "$LA" 2>/dev/null

echo "===== 汇总: PASS=$PASS FAIL=$FAIL ====="
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
