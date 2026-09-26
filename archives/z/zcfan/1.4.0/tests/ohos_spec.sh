#!/bin/sh
# tests/ohos_spec.sh — zcfan 1.4.0 HarmonyOS (aarch64-linux-ohos) 专项测试
#
# 用途: 验证本包在 HarmonyOS 上的「产物平台契约」——即交付物确实是面向 OHOS/musl
#       的 aarch64 PIE 可执行文件、在 OHOS 上可原生执行，并且**在保留上游全部严格
#       告警集的前提下**可从干净源码重建。这是与 test_package/（Conan L1 打包消费者
#       冒烟测试）互补的一层：test_package 验证「打包后的 CLI 行为」，本脚本验证
#       「二进制/ABI/工具链契约」。
#
# 用法:
#   sh tests/ohos_spec.sh <zcfan 二进制路径> [<源码树路径>]
#   sh tests/ohos_spec.sh /path/to/pkg/bin/zcfan /path/to/zcfan-1.4.0.work
#
# 前置: readelf（binutils/llvm）、make、clang 在 PATH 上；TMPDIR 可写（OHOS /tmp 只读）。
# 退出码: 0 = 全部通过；1 = 有失败。
#
# 说明: 上游 1.4.0 无运行时测试套件（见 test_package/MANIFEST.yml 清点证据），
#       因此本文件是新增的鸿蒙专项用例集，独立计数（5 条）。
# 风格: 全文不使用 $(...) / 反引号（OHOS readonly_tmp 加固约定，同 vamps 0.99.2）。
#       `|| true` / `2>/dev/null` 仅用于**诊断性**命令（回显失败现场、统计诊断条数），
#       这类命令的返回码不参与用例判定（判定依据是 RC + 计数 + 产物存在性）；
#       凡涉及用例输入前提的命令（如源码副本）一律显式判负，不吞错。
set -u
# -e 有意省略：每条用例都要先取 $? 再判定，失败须计数后汇总继续（首轮失败不终止）。
# pipefail 仅在本 shell 支持时启用（POSIX dash 无该选项，CI/宿主 /bin/sh 可能是 dash，
# 故写成受保护形式，避免在不支持该选项的 shell 上产生噪声/异常）。
if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi

BIN="${1:-}"
SRC="${2:-}"

if [ -z "${TMPDIR:-}" ] || [ ! -d "${TMPDIR:-}" ]; then
    for cand in "${TMP:-}" "${TEMP:-}" "${HOME:-/nonexistent}/tmp"; do
        if [ -n "$cand" ] && [ -d "$cand" ]; then TMPDIR="$cand"; break; fi
    done
fi
TMPDIR="${TMPDIR:-$PWD/tmp}"
# 目录已存在时 mkdir -p 返回 0；失败仅可能因路径不可写，随后写 $TMPDIR 下的中间/输出
# 文件时会显式暴露（用例判定读的是实际文件内容），故忽略返回码不会掩盖真实失败。
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR

PASS_COUNT=0
FAIL_COUNT=0
TOTAL=5

MUSL_INTERP="/lib/ld-musl-aarch64.so.1"

if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
    echo "[ohos_spec] FAIL: 未提供有效的 zcfan 二进制路径 (argv \$1='${BIN}')"
    echo 'HMBS_OHOS_SPEC_RESULT={"executed":false,"passed":false,"discovered":5,"passedCount":0,"reason":"binary path not provided"}'
    exit 1
fi

echo "[ohos_spec] zcfan HarmonyOS 专项测试"
echo "[ohos_spec] binary = $BIN"
echo "[ohos_spec] source = ${SRC:-(未提供，用例 5 将失败)}"

if ! command -v readelf >/dev/null 2>&1; then
    echo "[ohos_spec] FAIL: readelf 不在 PATH（前置条件缺失）"
    echo 'HMBS_OHOS_SPEC_RESULT={"executed":false,"passed":false,"discovered":5,"passedCount":0,"reason":"readelf missing"}'
    exit 1
fi

readelf -h "$BIN" >"$TMPDIR/ohos_hdr.txt" 2>&1
readelf -l "$BIN" >"$TMPDIR/ohos_phdr.txt" 2>&1
readelf -d "$BIN" >"$TMPDIR/ohos_dyn.txt" 2>&1

# ---------------------------------------------------------------- case 1
# 交付物必须是 aarch64 的 ELF64 位置无关可执行文件（OHOS PC 目标三元组）。
echo "[ohos_spec] case 1: ohos_elf_identity_aarch64_pie"
if grep -q "Class:.*ELF64" "$TMPDIR/ohos_hdr.txt" \
   && grep -q "Machine:.*AArch64" "$TMPDIR/ohos_hdr.txt" \
   && grep -q "Type:.*DYN" "$TMPDIR/ohos_hdr.txt"; then
    echo "ok: ohos_elf_identity_aarch64_pie (ELF64 / AArch64 / ET_DYN PIE)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: ohos_elf_identity_aarch64_pie"
    grep -E "Class|Machine|Type:" "$TMPDIR/ohos_hdr.txt" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 2
# 程序解释器必须是 OHOS/musl 的加载器：证明这是一份 musl 目标产物，而非
# 误链到 glibc 的 ld-linux（后者在 OHOS 上根本不存在，会直接 exec 失败）。
echo "[ohos_spec] case 2: ohos_musl_program_interpreter"
if grep -q "interpreter: $MUSL_INTERP" "$TMPDIR/ohos_phdr.txt"; then
    echo "ok: ohos_musl_program_interpreter (PT_INTERP = $MUSL_INTERP)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: ohos_musl_program_interpreter (期望 PT_INTERP = $MUSL_INTERP)"
    grep -i "interpreter" "$TMPDIR/ohos_phdr.txt" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 3
# 动态依赖收敛到 musl libc 单一项：zcfan 零三方依赖，不得出现 glibc 痕迹
# （libc.so.6 / ld-linux-*），也不得出现任何未预期的共享库。
echo "[ohos_spec] case 3: ohos_dynamic_deps_musl_only"
if grep -qiE "libc\.so\.6|ld-linux" "$TMPDIR/ohos_dyn.txt"; then
    echo "FAIL: ohos_dynamic_deps_musl_only (发现 glibc 痕迹)"
    grep -iE "NEEDED|libc\.so\.6|ld-linux" "$TMPDIR/ohos_dyn.txt" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
else
    grep -i "NEEDED" "$TMPDIR/ohos_dyn.txt" >"$TMPDIR/ohos_needed.txt" 2>/dev/null || true
    if [ ! -s "$TMPDIR/ohos_needed.txt" ]; then
        echo "FAIL: ohos_dynamic_deps_musl_only (无任何 DT_NEEDED？)"
        FAIL_COUNT=$((FAIL_COUNT+1))
    else
        grep -iv "libc\.so" "$TMPDIR/ohos_needed.txt" >"$TMPDIR/ohos_needed_bad.txt" 2>/dev/null || true
        if [ -s "$TMPDIR/ohos_needed_bad.txt" ]; then
            echo "FAIL: ohos_dynamic_deps_musl_only (出现 libc.so 之外的依赖)"
            cat "$TMPDIR/ohos_needed_bad.txt"
            FAIL_COUNT=$((FAIL_COUNT+1))
        else
            echo "ok: ohos_dynamic_deps_musl_only (DT_NEEDED 仅 libc.so)"
            PASS_COUNT=$((PASS_COUNT+1))
        fi
    fi
fi

# ---------------------------------------------------------------- case 4
# 真实执行：带任意参数时 main() 打印帮助并 return 0，不触碰任何硬件。
# 这是「产物在 OHOS 上可原生执行」的端到端证据（坏链接 rc=127，ABI 不符会段错误）。
echo "[ohos_spec] case 4: ohos_native_exec_usage_contract"
"$BIN" zcfan-ohos-spec </dev/null >"$TMPDIR/ohos_usage.out" 2>"$TMPDIR/ohos_usage.err"
RC=$?
if [ "$RC" -eq 0 ] \
   && grep -q "Zero-configuration ThinkPad fan daemon" "$TMPDIR/ohos_usage.out" 2>/dev/null \
   && grep -q "See the zcfan(1) man page for details" "$TMPDIR/ohos_usage.out" 2>/dev/null; then
    echo "ok: ohos_native_exec_usage_contract (rc=0, 帮助横幅输出核心契约匹配)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: ohos_native_exec_usage_contract (rc=$RC)"
    echo "[ohos_spec] stdout:"; cat "$TMPDIR/ohos_usage.out" 2>/dev/null || true
    echo "[ohos_spec] stderr:"; cat "$TMPDIR/ohos_usage.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 5
# 严格告警集下的干净重建：在源码副本上跑上游原样 `make`（仍带 -pedantic -Werror
# -Wconversion -Wstrict-prototypes …），要求 exit 0 且 **零** error/warning。
# 这是本包唯一适配补丁（去 GNU `##__VA_ARGS__`）的回归防线——若补丁丢失或被
# 上游行为回退，本用例立即变红。
echo "[ohos_spec] case 5: ohos_strict_flags_clean_rebuild"
if [ -z "$SRC" ] || [ ! -f "$SRC/zcfan.c" ]; then
    echo "FAIL: ohos_strict_flags_clean_rebuild (未提供含 zcfan.c 的源码树路径，argv \$2='${SRC}')"
    FAIL_COUNT=$((FAIL_COUNT+1))
elif ! command -v make >/dev/null 2>&1 || ! command -v clang >/dev/null 2>&1; then
    echo "FAIL: ohos_strict_flags_clean_rebuild (make/clang 不在 PATH)"
    FAIL_COUNT=$((FAIL_COUNT+1))
else
    WORK="$TMPDIR/zcfan-ohos-spec-$$"
    # 语料目录与源码副本是本用例的输入前提，失败即判 FAIL——不吞错，避免拿空目录"重建成功"
    if ! mkdir -p "$WORK"; then
        echo "FAIL: ohos_strict_flags_clean_rebuild (无法创建语料目录 $WORK)"
        FAIL_COUNT=$((FAIL_COUNT+1))
    elif ! cp -a "$SRC/." "$WORK/"; then
        echo "FAIL: ohos_strict_flags_clean_rebuild (源码副本失败: $SRC -> $WORK)"
        FAIL_COUNT=$((FAIL_COUNT+1))
    else
        # 强制重建：cp -a 保留 mtime，若副本内自带产物则源码不比产物新，make 会
        # "Nothing to be done" 空转、用例失去意义。刷新源文件时间戳确保真的重新编译
        # （touch 为 POSIX 基本工具；若其失败，下方 COMPILED 断言会把空转判为 FAIL，
        #  不会静默通过，故此处可忽略其返回码）。
        touch "$WORK/zcfan.c" 2>/dev/null || true
        ( cd "$WORK" && make -j1 CC=clang ) >"$TMPDIR/ohos_rebuild.log" 2>&1
        RC=$?
        # grep -c 零匹配时返回 1，属预期（= 0 条诊断），故忽略返回码、只取计数值
        grep -c "error:" "$TMPDIR/ohos_rebuild.log" >"$TMPDIR/ohos_err_n.txt" 2>/dev/null || true
        grep -c "warning:" "$TMPDIR/ohos_rebuild.log" >"$TMPDIR/ohos_warn_n.txt" 2>/dev/null || true
        ERR_N=$(cat "$TMPDIR/ohos_err_n.txt" 2>/dev/null)
        WARN_N=$(cat "$TMPDIR/ohos_warn_n.txt" 2>/dev/null)
        ERR_N=${ERR_N:-0}
        WARN_N=${WARN_N:-0}
        # 必须真的发生编译：若传入的源码树自带产物，make 会 "Nothing to be done" 直接空转，
        # 那样本用例就失去意义（假通过）。故要求日志出现编译调用行。
        COMPILED=0
        if grep -q "zcfan\.c -o zcfan" "$TMPDIR/ohos_rebuild.log" 2>/dev/null; then
            COMPILED=1
        fi
        # 确定性重建：重编译产物应与参考二进制逐字节一致（同一源码 + 同一上游严格告警集）
        SAME=0
        if [ -x "$BIN" ] && cmp -s "$WORK/zcfan" "$BIN"; then
            SAME=1
        fi
        if [ "$RC" -eq 0 ] && [ "$ERR_N" -eq 0 ] && [ "$WARN_N" -eq 0 ] \
           && [ -x "$WORK/zcfan" ] && [ "$COMPILED" -eq 1 ] && [ "$SAME" -eq 1 ]; then
            echo "ok: ohos_strict_flags_clean_rebuild (exit 0, error=0 warning=0, 真实编译且与参考二进制逐字节一致)"
            PASS_COUNT=$((PASS_COUNT+1))
        else
            echo "FAIL: ohos_strict_flags_clean_rebuild (exit=$RC error=$ERR_N warning=$WARN_N compiled=$COMPILED byte_identical=$SAME)"
            # 仅诊断性回显：日志缺失不影响判定（上方已据 RC/计数判负），故忽略 tail 返回码
            tail -30 "$TMPDIR/ohos_rebuild.log" 2>/dev/null || true
            FAIL_COUNT=$((FAIL_COUNT+1))
        fi
    fi
fi

echo "[ohos_spec] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of $TOTAL)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq "$TOTAL" ]; then
    echo 'HMBS_OHOS_SPEC_RESULT={"executed":true,"passed":true,"command":"sh tests/ohos_spec.sh","discovered":5,"passedCount":5,"failedCount":0,"skippedCount":0}'
    exit 0
else
    echo 'HMBS_OHOS_SPEC_RESULT={"executed":true,"passed":false,"command":"sh tests/ohos_spec.sh","discovered":5,"passedCount":'"$PASS_COUNT"',"failedCount":'"$FAIL_COUNT"',"skippedCount":0}'
    exit 1
fi
