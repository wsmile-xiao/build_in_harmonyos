#!/bin/sh
# test_package/test_skewer.sh — skewer 0.2.2 鸿蒙消费者测试（消费者视角，10 条断言）
#
# 用法: sh test_skewer.sh <pkg>/bin/skewer [scratch_dir]
#   $1 = test_package/conanfile.py 传入的**已安装包产物**绝对路径（不是构建树中间产物）
#   $2 = 可写 scratch 目录（由 conanfile 传入包构建目录；OHOS /tmp 只读，故不用 /tmp）
#
# 断言清单（口径对齐 docs/TEST_QUALITY_SPEC.md 层 2；全部真实执行被测二进制）:
#   A1 版本输出（稳定字符串精确断言，不是恒真 rc 判断）
#   A2 --help 用法文本（标题行 + USAGE 行 + Adapter 选项段）
#   A3 无参数调用的诊断语义（rc=1 + "No input file specified" + 提示 --help）
#   A4 版本字符串确实内嵌在产物字节里（grep -a 直读 ELF）
#   A5 ELF 架构断言（ELF64 + AArch64 + DYN/PIE）
#   A6 平台解释器断言（.interp 与 readelf -l 双向一致 = musl，而非 glibc）
#   A7 NEEDED 集合断言（只允许 musl libc.so 与 OHOS libc++_shared.so；显式排除 glibc 专有 soname）
#   A8 OHOS ELF 标记 + RPATH/RUNPATH 断言（.codesign ×1 + .note.ohos.ident + 无 RPATH/RUNPATH）
#   A9 功能断言：真实 FASTQ 全管线，适配子在 42bp 处被精确剪除，日志点名 fixture
#   A10 缺陷回归断言：**奇数条**（5 条）FASTQ 全管线必须 5 进 5 出，且不得出现
#      'Malformed fastq record' 指纹 —— 钉死上游 plain-char EOF 哨兵缺陷
#      （知识库 DRAFT-8543；本包 patches/0001-fix-char-eof-sentinel.patch）
#   另附「产物内无宿主绝对路径泄漏」证据行（并入 A4/A8 的静态扫描维度，如实打印）
#
# 能力缺口口径说明：本包**没有**需要 test_skipped 的用例 —— skewer 是纯
# stdin/文件 I/O 的 FASTQ 处理器，不依赖真终端、sixel、GPU、/dev 设备；上游
# 静态测试数为 0（见 MANIFEST.yml 的三条清点证据），所以这里不是"没环境所以不跑"，
# 而是"可执行的全部执行"。任何一项失败都会如实计入 FAIL，SKIP 恒为 0。
set -u

PASS=0
FAIL=0
SKIP=0
TOTAL=10

BIN="${1:-}"
SCRATCH="${2:-.}"

emit_result() {
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"sh test_skewer.sh <pkg>/bin/skewer","discovered":%d,"passedCount":%d,"failedCount":%d,"skippedCount":%d,"reason":"%s"}\n' \
        "$1" "$TOTAL" "$2" "$3" "$4" "$5"
}

if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
    echo "[FAIL] 产物不存在或未传参: BIN=${BIN:-<empty>}"
    emit_result false 0 1 0 "packaged binary not found"
    exit 1
fi
BIN_DIR="$(cd "$(dirname "$BIN")" && pwd)"
BIN="$BIN_DIR/$(basename "$BIN")"

mkdir -p "$SCRATCH" 2>/dev/null || true
SCRATCH="$(cd "$SCRATCH" 2>/dev/null && pwd || echo "$PWD")"
WORK="$SCRATCH/skewer-test.$$"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "[FAIL] scratch 不可写: $SCRATCH"; emit_result false 0 1 0 "scratch not writable"; exit 1; }
trap 'rm -rf "$WORK"' EXIT INT TERM

ok()  { PASS=$((PASS + 1)); echo "[PASS] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "[FAIL] $1${2:+ — $2}"; }

echo "[test] binary : $BIN"
echo "[test] scratch: $WORK"
ls -l "$BIN" 2>&1 || true

READELF=""
for cand in /data/service/hnp/bin/llvm-readelf /data/service/hnp/bin/readelf; do
    if [ -f "$cand" ]; then READELF="$cand"; break; fi
done
if [ -z "$READELF" ]; then
    for cand in llvm-readelf readelf; do
        if command -v "$cand" >/dev/null 2>&1; then READELF="$cand"; break; fi
    done
fi
echo "[test] readelf: ${READELF:-<none>}"

# ── A1 版本输出（精确字符串）─────────────────────────────────────────────
"$BIN" --version >"$WORK/ver.out" 2>"$WORK/ver.err"
rc=$?
if [ "$rc" -eq 0 ] \
   && grep -qF 'skewer version: 0.2.2' "$WORK/ver.out" \
   && grep -qF 'Author: Hongshan Jiang' "$WORK/ver.out"; then
    ok "A1 skewer --version 输出精确版本串且 rc=0"
else
    bad "A1 skewer --version 输出异常" "rc=$rc out=$(tr '\n' '|' <"$WORK/ver.out" 2>/dev/null | cut -c1-160) err=$(tr '\n' '|' <"$WORK/ver.err" 2>/dev/null | cut -c1-160)"
fi

# ── A2 --help 用法文本 ───────────────────────────────────────────────────
"$BIN" --help >"$WORK/help.out" 2>"$WORK/help.err"
if grep -qF 'Skewer (A fast and accurate adapter trimmer for paired-end reads)' "$WORK/help.out" \
   && grep -qF 'USAGE: skewer [options] <reads.fastq> [paired-reads.fastq]' "$WORK/help.out" \
   && grep -qF 'Adapter:' "$WORK/help.out"; then
    ok "A2 skewer --help 打印完整用法（标题行 + USAGE 行 + Adapter 选项段）"
else
    bad "A2 skewer --help 用法文本缺失" "$(tr '\n' '|' <"$WORK/help.out" 2>/dev/null | cut -c1-200)"
fi

# ── A3 无参数调用的诊断语义 ──────────────────────────────────────────────
(cd "$WORK" && "$BIN") >"$WORK/noargs.out" 2>"$WORK/noargs.err"
rc=$?
if [ "$rc" -eq 1 ] \
   && grep -qF 'skewer (0.2.2): No input file specified' "$WORK/noargs.err" \
   && grep -qF 'Usage: skewer [options] <file> [file2]' "$WORK/noargs.err"; then
    ok "A3 无参数调用给出 rc=1 与参数解析层诊断（证明解析路径可达、非静默崩溃）"
else
    bad "A3 无参数诊断异常" "rc=$rc err=$(tr '\n' '|' <"$WORK/noargs.err" 2>/dev/null | cut -c1-200)"
fi

# ── A4 版本串确实内嵌于产物 ──────────────────────────────────────────────
# ⚠ 2026-09-28 收尾-8 整改（与 iroffer 8cc095f334 同方）：CI 侧 test() 走 conanrun
# env，profile 只把 hnp 挂进 [buildenv] ⇒ 落回 toybox grep 0.8.12，而它对**含 NUL
# 的二进制**即使用 -a 也静默返回 1（本机双臂实测同一件 182784B 产物：hnp GNU grep
# 3.12 rc=0 / toybox rc=1，连纯字面 'skewer' 都 0 命中；cat 喂流与 stdin 重定向同样
# rc=1）。改为「先 tr 去掉 NUL 再 grep」：匹配模式本身不含 NUL ⇒ 去 NUL 不改变匹配
# 语义，tr/grep 又是 toybox 与 GNU 共有的基础工具（两臂均 rc=0）。断言条数与含义不变。
if tr -d '\000' < "$BIN" | LC_ALL=C grep -qF 'skewer version: ' ; then
    ok "A4 版本格式串内嵌在 ELF 字节中（tr 去 NUL 后 grep，产物即 0.2.2 构建，非替身）"
else
    bad "A4 ELF 中找不到版本格式串" "$BIN"
fi

# ── A5..A8 平台断言（依赖 readelf；缺工具一律计 FAIL，不做跳过）──────────
if [ -z "$READELF" ]; then
    bad "A5 llvm-readelf/readelf 不可用，无法校验 ELF 架构" "no readelf on host"
    bad "A6 llvm-readelf/readelf 不可用，无法校验 .interp" "no readelf on host"
    bad "A7 llvm-readelf/readelf 不可用，无法校验 NEEDED" "no readelf on host"
    bad "A8 llvm-readelf/readelf 不可用，无法校验 .codesign/.note.ohos.ident" "no readelf on host"
else
    "$READELF" -h "$BIN" >"$WORK/elfh.out" 2>&1
    if grep -q 'Class:.*ELF64' "$WORK/elfh.out" \
       && grep -q 'Machine:.*AArch64' "$WORK/elfh.out" \
       && grep -q 'Type:.*DYN' "$WORK/elfh.out"; then
        ok "A5 ELF 架构断言通过（ELF64 + AArch64 + DYN/PIE）"
    else
        bad "A5 ELF 头不符合鸿蒙 aarch64 预期" "$(tr '\n' '|' <"$WORK/elfh.out" | cut -c1-200)"
    fi

    "$READELF" -p .interp "$BIN" >"$WORK/interp.out" 2>&1
    "$READELF" -l "$BIN" >"$WORK/phdrs.out" 2>&1
    if grep -qF '/lib/ld-musl-aarch64.so.1' "$WORK/interp.out" \
       && grep -qF 'Requesting program interpreter: /lib/ld-musl-aarch64.so.1' "$WORK/phdrs.out"; then
        ok "A6 解释器为 musl（.interp 与 readelf -l 双向一致），非 glibc"
    else
        bad "A6 解释器断言失败" "interp=$(tr '\n' '|' <"$WORK/interp.out" | cut -c1-120)"
    fi

    "$READELF" -d "$BIN" >"$WORK/dyn.out" 2>&1
    NEEDED="$(grep -o 'Shared library: \[[^]]*\]' "$WORK/dyn.out" | sed 's/.*\[\(.*\)\]/\1/' | sort -u)"
    printf '# skewer NEEDED 集合（实测原文）\n%s\n' "$NEEDED" >"$WORK/needed.txt" 2>&1
    unexpected=""
    for lib in $NEEDED; do
        case "$lib" in
            libc.so|libc++_shared.so) ;;
            *) unexpected="$unexpected $lib" ;;
        esac
    done
    glibc_hit=""
    for so in libc.so.6 libpthread.so.0 librt.so.1 libm.so.6 libdl.so.2 libgcc_s.so.1; do
        case " $NEEDED " in
            *" $so "*) glibc_hit="$glibc_hit $so" ;;
        esac
    done
    if [ -n "$NEEDED" ] && [ -z "$unexpected" ] && [ -z "$glibc_hit" ]; then
        ok "A7 NEEDED 集合符合预期（$(printf '%s' "$NEEDED" | tr '\n' ' ')= 仅 musl libc + OHOS libc++，无 glibc 专有 soname）"
    else
        bad "A7 NEEDED 集合含预期外项" "needed=$(printf '%s' "$NEEDED" | tr '\n' ' ') unexpected=$unexpected glibc=$glibc_hit"
    fi

    "$READELF" -SW "$BIN" >"$WORK/sects.out" 2>&1
    ncs="$(grep -c '\.codesign' "$WORK/sects.out" 2>/dev/null)"
    [ -n "$ncs" ] || ncs=0
    nohrp=1
    grep -qE '\b(RPATH|RUNPATH)\b' "$WORK/dyn.out" && nohrp=0
    if [ "$ncs" -eq 1 ] && grep -q 'note\.ohos\.ident' "$WORK/sects.out" && [ "$nohrp" -eq 1 ]; then
        ok "A8 OHOS ELF 标记齐备（.codesign x1 + .note.ohos.ident）且无 RPATH/RUNPATH"
    else
        bad "A8 OHOS ELF 标记/RPATH 断言失败" "codesign_count=$ncs note_ohos=$(grep -c 'note\.ohos\.ident' "$WORK/sects.out" 2>/dev/null) rpath=$([ "$nohrp" -eq 1 ] && echo none || echo present)"
    fi
fi

# ── 产物内无宿主绝对路径泄漏（静态扫描证据行）────────────────────────────
HOSTPATHS="$(LC_ALL=C grep -a -o -E '(/storage/|/home/|/data/service/hnp|/tmp/|/var/tmp/|/build/)[A-Za-z0-9._+-]*' "$BIN" 2>/dev/null | sort -u)"
if [ -z "$HOSTPATHS" ]; then
    echo "[info] 静态扫描: 产物内无宿主机构建/安装路径（/devcloud、/srv 前缀属 SDK 工具链自带出处，非本机路径，如实记录）"
else
    echo "[info] 静态扫描: 产物内出现宿主路径 -> $(printf '%s' "$HOSTPATHS" | tr '\n' ' ')"
fi

# ── A9 功能断言：真实 FASTQ 适配子剪切 ───────────────────────────────────
# fixture: 8 条 100bp 读段，第 43bp 起为 Illumina 适配子 AGATCGGAAGAGCGTCGTG...
# 期望: skewer -t 1 -x AGATCGGAAGAGC -o t in.fastq
#       -> t-trimmed.fastq 内 8 条读段，序列与质量行长度均为 42（适配子整段被剪）
SEQ='GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAAGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGCTCTTAAGCAGTTACTGGGACTG'
QUAL='IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII'
FULL="$WORK/in.fastq"
: >"$FULL"
i=1
while [ "$i" -le 8 ]; do
    printf '@read%d\n%s\n+\n%s\n' "$i" "$SEQ" "$QUAL" >>"$FULL"
    i=$((i + 1))
done
in_records=$(grep -c '^@read' "$FULL" 2>/dev/null)
[ -n "$in_records" ] || in_records=0
(cd "$WORK" && "$BIN" -t 1 -x 'AGATCGGAAGAGC' -o t in.fastq) >"$WORK/run.out" 2>&1
rc=$?
out_file="$WORK/t-trimmed.fastq"
log_file="$WORK/t-trimmed.log"
out_records=0
[ -f "$out_file" ] && out_records=$(grep -c '^@read' "$out_file" 2>/dev/null)
[ -n "$out_records" ] || out_records=0
seq_lens="$(awk 'NR%4==2 { print length($0) }' "$out_file" 2>/dev/null | sort -u | tr '\n' ',')"
qual_lens="$(awk 'NR%4==0 { print length($0) }' "$out_file" 2>/dev/null | sort -u | tr '\n' ',')"
if [ "$rc" -eq 0 ] && [ -f "$out_file" ] && [ "$in_records" -eq 8 ] \
   && [ "$out_records" -eq 8 ] && [ "$seq_lens" = "42," ] && [ "$qual_lens" = "42," ] \
   && grep -qF '8 reads processed' "$WORK/run.out" \
   && grep -qF 'in.fastq' "$log_file" && grep -qF 't-trimmed.fastq' "$log_file"; then
    ok "A9 真实 FASTQ 全管线：8 条 100bp 读段的适配子在 42bp 处被精确剪除，日志点名 fixture"
else
    bad "A9 功能剪切断言失败" "rc=$rc in=$in_records out=$out_records seq_lens=$seq_lens qual_lens=$qual_lens run=$(tr '\n' '|' <"$WORK/run.out" 2>/dev/null | cut -c1-240)"
fi

# ── A10 缺陷回归断言：奇数条 FASTQ 不得丢最后一条（EOF 哨兵落进 plain char）───
# 上游 src/fastq.h 的 cFQ::tag 与 src/fastq.cpp 的 cFQ::readRecord() 局部 c 原本都是
# plain char 承接 fgetc() 的返回值再与 EOF 比较。OHOS 目标的 plain char 默认**无符号**
# （clang -dumpmachine = aarch64-unknown-linux-ohos，limits.h 的 CHAR_MIN==0，
# 预定义 __CHAR_UNSIGNED__）⇒ EOF(-1) 不可表示 ⇒ 三处 EOF 判定全是死代码
# （clang 编译期就报 -Wtautological-constant-out-of-range-compare）。
# 后果：文件读尽时 readRecord() 返回 -2（"Malformed fastq record N: no '@' for id"）
# 而不是 -1，src/main.cpp 的工作线程按"解析错误"整块丢弃该 block 里已读到的记录；
# 块大小 = nBasicSize*n_threads，nBasicSize = (len>800MB)?10:(len/100MB+2)（main.cpp:819-821）
# ⇒ < 100MB 的输入恒为 2 ⇒ 本用例（KB 级、-t 1）**记录数为奇数必然丢掉最后一条**；
#   更大的输入或多线程会丢 1..blockSize-1 条（本断言只钉死 KB 级 + -t 1 这一档）。
# patches/0001-fix-char-eof-sentinel.patch 只把这两个接收变量 widen 成 int。
# 判据三重钉死：skewer 自报的 "5 reads processed" + 产物里 @read5 确实在 + 无 malformed 指纹。
FULL5="$WORK/in5.fastq"
: >"$FULL5"
i=1
while [ "$i" -le 5 ]; do
    printf '@read%d\n%s\n+\n%s\n' "$i" "$SEQ" "$QUAL" >>"$FULL5"
    i=$((i + 1))
done
in5=$(grep -c '^@read' "$FULL5" 2>/dev/null)
[ -n "$in5" ] || in5=0
(cd "$WORK" && "$BIN" -t 1 -x 'AGATCGGAAGAGC' -o t5 in5.fastq) >"$WORK/run5.out" 2>&1 </dev/null
rc=$?
out5_file="$WORK/t5-trimmed.fastq"
out5=0
[ -f "$out5_file" ] && out5=$(grep -c '^@read' "$out5_file" 2>/dev/null)
[ -n "$out5" ] || out5=0
seq5="$(awk 'NR%4==2 { print length($0) }' "$out5_file" 2>/dev/null | sort -u | tr '\n' ',')"
qual5="$(awk 'NR%4==0 { print length($0) }' "$out5_file" 2>/dev/null | sort -u | tr '\n' ',')"
mal5=$(grep -c 'Malformed fastq record' "$WORK/run5.out" 2>/dev/null)
[ -n "$mal5" ] || mal5=0
last5=0
[ -f "$out5_file" ] && grep -q '^@read5' "$out5_file" && last5=1
if [ "$rc" -eq 0 ] && [ "$in5" -eq 5 ] && [ "$out5" -eq 5 ] && [ "$last5" -eq 1 ] \
   && [ "$seq5" = "42," ] && [ "$qual5" = "42," ] \
   && grep -qF '5 reads processed' "$WORK/run5.out" \
   && [ "$mal5" -eq 0 ]; then
    ok "A10 奇数条回归：5 条 100bp 读段全部处理（5/5 输出、@read5 未丢、0 条 malformed 诊断、42bp 剪切不回归）"
else
    bad "A10 奇数条记录被丢弃（EOF 哨兵缺陷复发）" "rc=$rc in=$in5 out=$out5 last_read5=$last5 seq_lens=$seq5 qual_lens=$qual5 malformed=$mal5 run=$(tr '\n' '|' <"$WORK/run5.out" 2>/dev/null | cut -c1-240)"
fi

# ── 汇总与机器可读标记 ───────────────────────────────────────────────────
passed=true
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$TOTAL" ]; then
    passed=false
fi
emit_result "$passed" "$PASS" "$FAIL" "$SKIP" "see per-assertion lines above"
# 上游测试申报（同源证据见 test_package/MANIFEST.yml upstream_test_audit）:
# shellcheck disable=SC2016
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"skewer 0.2.2 上游 tar 包共 10 个文件：无 tests/test/t 目录、make -n check 报 No rule to make target、文件清单内无测试源，故上游静态测试数为 0"}\n'

echo "=== test_package summary: ${PASS}/${TOTAL} passed, ${FAIL} failed, ${SKIP} skipped ==="
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$TOTAL" ]; then
    exit 1
fi
exit 0
