#!/bin/bash
# test_package/test.sh -- sockstat 0.4.2 消费者测试（31 断言）
#
# 全部断言都作用于本包产出的 bin/sockstat（真实执行或真实 ELF 取证），无空壳。
#
# 执行环境三态：
#   * CI profile 跑在真机 HarmonyOS PC（/data/service/hnp/bin/clang），aarch64
#     产物原生执行；
#   * x86_64 运行器上若存在 qemu-aarch64，同一产物经 qemu 执行；
#   * 两者都不可用时，运行期断言降级为 SKIP，T1 产物取证断言照常执行
#     （纪律同 archives/n/net-tools/2.1/test_package/test.sh）。
#
# OHOS 沙箱权限模型（实测依据见本仓 archives/n/net-tools/2.1/reports/
# manual-runtime-evidence.md 的 12/12 /proc/net EACCES 矩阵）：普通 uid 下
# /proc/net/{tcp,udp,raw,tcp6,udp6,raw6,unix} 内容不可读。上游对缺失文件调用
# handle_missing_file() -> abort()，因此真机上"读表"类调用会 SIGABRT 并打印
# "can not open file /proc/net/..."。这是平台权限差异而非配方缺陷，故计入
# RESTRICTED（不计 FAIL）；若读表可用则计入 PASS。两种情况都必须给出明确诊断
# 而不是静默输出空表——这条由 T4 单独断言。
#
# 例外分类 DEFECT：上游 0.4.2 自身缺陷（与平台无关，Linux 上同样复现），
# 记录证据但**仅限已确认的两种已知结局**（rc=139 SIGSEGV / rc=0 未复现）；
# 任何其他退出码一律 fail——DEFECT 档不得变成兜底垃圾桶。
# 修与不修的取舍见 notes.md。
#
# 不用 `set -o pipefail`：脚本里大量 `... | head -N`，head 提前关闭管道会
# 触发 SIGPIPE(141) 并被 pipefail 误判为失败。管道环节的失败由各断言显式判据
# （grep -q / 空结果检查）承担。
set -u

EXE="${1:-}"
if [ -z "${EXE}" ] || [ ! -f "${EXE}" ]; then
    echo "FAIL: sockstat binary not provided or not a file: '${EXE}'"
    exit 1
fi
EXE="$(cd "$(dirname "${EXE}")" && pwd)/$(basename "${EXE}")"
PKG_ROOT="$(cd "$(dirname "${EXE}")/.." && pwd)"

PASS=0; SKIP=0; FAIL=0; RESTRICTED=0; DEFECT=0
TOTAL_ASSERTIONS=31

pass()     { echo "OK: $1"; PASS=$((PASS + 1)); }
skip()     { echo "SKIP: $1"; SKIP=$((SKIP + 1)); }
fail()     { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
restrict() { echo "RESTRICTED: $1"; RESTRICTED=$((RESTRICTED + 1)); }
defect()   { echo "KNOWN_UPSTREAM_DEFECT: $1"; DEFECT=$((DEFECT + 1)); }

# ── 运行器选择 ────────────────────────────────────────────────────────────
MACHINE="$(uname -m 2>/dev/null || echo unknown)"
SKIP_EXEC=0
case "${MACHINE}" in
    aarch64|arm64)
        RUNNER=""
        RUNNER_DESC="native (${MACHINE})"
        ;;
    *)
        if command -v qemu-aarch64 >/dev/null 2>&1; then
            RUNNER="qemu-aarch64"
            [ -n "${OHOS_SYSROOT:-}" ] && RUNNER="${RUNNER} -L ${OHOS_SYSROOT}"
            RUNNER_DESC="qemu-aarch64${OHOS_SYSROOT:+ -L \$OHOS_SYSROOT}"
        else
            RUNNER="__none__"
            RUNNER_DESC="unavailable (no native aarch64, no qemu-aarch64)"
        fi
        ;;
esac
echo "[test] binary : ${EXE}"
echo "[test] pkg    : ${PKG_ROOT}"
echo "[test] runner : ${RUNNER_DESC}"

# TOOL_RC=199 统一表示"本环境无法执行该产物"
TOOL_RC=0; TOOL_OUT=""
run_sockstat() {
    TOOL_OUT=""; TOOL_RC=199
    [ "${SKIP_EXEC}" -eq 1 ] && return 0
    TOOL_OUT="$(${RUNNER} "${EXE}" "$@" 2>&1)"
    TOOL_RC=$?
    case "${TOOL_OUT}" in
        *"Exec format error"*|*"cannot execute binary file"*)
            SKIP_EXEC=1; TOOL_RC=199 ;;
    esac
    if [ "${TOOL_RC}" -eq 255 ] && echo "${TOOL_OUT}" | grep -q "Could not open"; then
        SKIP_EXEC=1; TOOL_RC=199
    fi
    if [ "${TOOL_RC}" -eq 126 ] || [ "${TOOL_RC}" -eq 127 ]; then
        SKIP_EXEC=1; TOOL_RC=199
    fi
    return 0
}

first_line() { printf '%s' "${TOOL_OUT}" | sed -n '1p' | cut -c1-110; }

# 字节取证：返回指定偏移起 count 字节的小端十六进制串（不依赖 readelf）
elf_bytes() {
    dd if="$1" bs=1 skip="$2" count="$3" 2>/dev/null | od -An -tx1 | tr -d ' \n'
}

# ── T1 产物完整性（6 断言）────────────────────────────────────────────────
echo "[T1] 产物完整性取证"
if [ -x "${EXE}" ]; then
    pass "bin/sockstat 存在且可执行"
else
    fail "bin/sockstat 缺失或不可执行"
fi

MAGIC="$(elf_bytes "${EXE}" 0 4)"
if [ "${MAGIC}" = "7f454c46" ]; then
    pass "ELF magic 正确 (7f454c46)"
else
    fail "ELF magic 错误: '${MAGIC}'"
fi

MACH="$(elf_bytes "${EXE}" 18 2)"
if [ "${MACH}" = "b700" ]; then
    pass "e_machine=183 (AArch64) -- 目标三元组 aarch64-linux-ohos"
else
    fail "e_machine 非 AArch64: '${MACH}' (期望 b700)"
fi

ETYPE="$(elf_bytes "${EXE}" 16 2)"
if [ "${ETYPE}" = "0300" ]; then
    pass "e_type=ET_DYN (PIE 可执行)"
else
    fail "e_type 非 ET_DYN: '${ETYPE}' (期望 0300)"
fi

if [ -s "${PKG_ROOT}/share/man/man1/sockstat.1" ]; then
    pass "man page share/man/man1/sockstat.1 已随包安装"
else
    fail "share/man/man1/sockstat.1 缺失或为空"
fi

if [ -s "${PKG_ROOT}/licenses/LICENSE" ]; then
    pass "licenses/LICENSE 已随包安装"
else
    fail "licenses/LICENSE 缺失或为空"
fi

# ── T2 参数解析（6 断言；全部在打开 /proc/net 之前返回，故真机必过）──────
echo "[T2] 命令行参数解析（不触碰 /proc/net）"
run_sockstat -h
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "-h 产物不可执行（${RUNNER_DESC}）"
elif [ "${TOOL_RC}" -eq 1 ] && echo "${TOOL_OUT}" | grep -q "usage:"; then
    pass "-h 打印 usage 并以 rc=1 退出: $(first_line)"
else
    fail "-h rc=${TOOL_RC} 期望 rc=1 + usage: $(first_line)"
fi

run_sockstat -h
MISSING_OPT=""
for frag in '[-46clhu]' '[-p ports]' '[-U uid|user]' '[-G gid|group]' \
            '[-P pid|process]' '[-R protocol]' '[-o]'; do
    echo "${TOOL_OUT}" | grep -qF -- "${frag}" || MISSING_OPT="${MISSING_OPT} ${frag}"
done
if [ "${SKIP_EXEC}" -eq 1 ]; then
    skip "usage 选项覆盖度 产物不可执行"
elif [ -z "${MISSING_OPT}" ]; then
    pass "usage 覆盖上游全部选项（-46clhu -p -U -G -P -R -o）"
else
    fail "usage 缺少选项片段:${MISSING_OPT}"
fi

run_sockstat -Z
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "-Z 非法选项 产物不可执行"
elif [ "${TOOL_RC}" -eq 1 ] && echo "${TOOL_OUT}" | grep -q "unrecognized option"; then
    pass "-Z 非法选项被拒绝并打印 usage: $(first_line)"
else
    fail "-Z rc=${TOOL_RC} 期望 rc=1 + unrecognized option: $(first_line)"
fi

run_sockstat -p 99999
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "-p 99999 越界端口 产物不可执行"
elif [ "${TOOL_RC}" -eq 1 ] && echo "${TOOL_OUT}" | grep -q "invalid port number"; then
    pass "-p 99999 越界端口被拒（rc=1 invalid port number）"
else
    fail "-p 99999 rc=${TOOL_RC} 期望 rc=1: $(first_line)"
fi

run_sockstat -p abc
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "-p abc 非法端口 产物不可执行"
elif [ "${TOOL_RC}" -eq 1 ] && echo "${TOOL_OUT}" | grep -q "syntax error in port range"; then
    pass "-p abc 非法端口被拒（rc=1 syntax error in port range）"
else
    fail "-p abc rc=${TOOL_RC} 期望 rc=1: $(first_line)"
fi

run_sockstat -p 0-1
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "-p 0-1 合法区间解析 产物不可执行"
elif echo "${TOOL_OUT}" | grep -q "syntax error in port range\|invalid port number"; then
    fail "-p 0-1 合法区间被误拒: $(first_line)"
elif [ "${TOOL_RC}" -ne 0 ] \
     && ! echo "${TOOL_OUT}" | grep -q "can not open file /proc/net/"; then
    # 合法区间必须一路走到读表阶段；除"读表成功(0)"与"读表受限(沙箱 abort)"
    # 两种合法结局外，任何退出码都说明区间解析把程序带进了别的分支
    fail "-p 0-1 合法区间未走到读表阶段（rc=${TOOL_RC}）: $(first_line)"
else
    pass "-p 0-1 合法区间解析通过（未误报端口语法错，且已进入读表阶段）"
fi

# ── T3 读表路径（11 断言；真机可能 RESTRICTED）──────────────────────────
echo "[T3] 读表路径（每种调用都必须给出表头或明确权限诊断）"
check_table() {
    local label="$1"; shift
    run_sockstat "$@"
    if [ "${TOOL_RC}" -eq 199 ]; then
        skip "${label} 产物不可执行（${RUNNER_DESC}）"
    elif [ "${TOOL_RC}" -eq 0 ] \
         && echo "${TOOL_OUT}" | head -1 | grep -q "USER" \
         && echo "${TOOL_OUT}" | head -1 | grep -q "PROTO"; then
        pass "${label} 输出 sockstat 表头: $(first_line)"
    elif echo "${TOOL_OUT}" | grep -q "can not open file /proc/net/"; then
        restrict "${label} OHOS 沙箱 /proc/net EACCES（上游如实报缺失并 abort）: $(first_line)"
    else
        fail "${label} rc=${TOOL_RC} 既无表头也无 /proc/net 诊断: $(first_line)"
    fi
}
check_table "默认（无参数）"
check_table "-4 仅 IPv4" -4
check_table "-6 仅 IPv6" -6
check_table "-u 仅 unix 套接字" -u
check_table "-l 仅监听" -l
check_table "-c 仅已连接" -c
check_table "-R tcp 按协议" -R tcp
check_table "-R udp 按协议" -R udp
check_table "-P $$ 按 PID" -P $$
check_table "-U root 按用户" -U root
check_table "-o 旧行为组合" -o

# ── T4 鸿蒙特有：沙箱权限模型下的自包含与如实报错（4 断言）──────────────
echo "[T4] 鸿蒙特有（OHOS 沙箱 /proc/net 权限模型 + 产物自包含）"
READELF=""
for cand in readelf llvm-readelf eu-readelf; do
    if command -v "${cand}" >/dev/null 2>&1; then READELF="${cand}"; break; fi
done
if [ -z "${READELF}" ]; then
    skip "NEEDED 仅 libc.so（无 readelf 可用，无法取证）"
else
    NEEDED="$(${READELF} -d "${EXE}" 2>/dev/null | grep -o 'NEEDED.*\[\([^]]*\)\]' \
            | sed 's/.*\[\(.*\)\]/\1/' | sort | tr '\n' ' ')"
    if [ -z "${NEEDED// /}" ]; then
        # 解析不出 NEEDED 就断言"仅 libc.so"是空过，必须判 FAIL
        fail "readelf -d 未解析出任何 NEEDED 项，无法证明依赖面（输出: ${NEEDED:-<空>}）"
    else
        NONLIBC="$(echo "${NEEDED}" | tr ' ' '\n' | grep -v '^libc\.so$' | grep -v '^$')"
        if [ -z "${NONLIBC}" ]; then
            pass "动态依赖仅 libc.so（NEEDED='${NEEDED}'），无宿主第三方 .so 污染"
        else
            fail "存在非 libc.so 动态依赖: '${NONLIBC}'"
        fi
    fi
fi

SHARED_FOUND="$(find "${PKG_ROOT}" -name '*.so' -o -name '*.so.*' -o -name '*.a' 2>/dev/null | head -5)"
if [ -z "${SHARED_FOUND}" ]; then
    pass "包内无 .so/.a（不污染 /lib、/lib64，R26 口径）"
else
    fail "包内出现共享/静态库: $(echo "${SHARED_FOUND}" | tr '\n' ' ')"
fi

run_sockstat
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "受限诊断信息 产物不可执行"
elif echo "${TOOL_OUT}" | grep -q "can not open file /proc/net/"; then
    if echo "${TOOL_OUT}" | grep -q "USER.*PROTO"; then
        fail "受限态同时输出表头与缺失诊断，行为自相矛盾"
    else
        pass "受限态输出明确诊断（点名 /proc/net/<file>），未静默输出空表"
    fi
elif [ "${TOOL_RC}" -eq 0 ] && echo "${TOOL_OUT}" | head -1 | grep -q "USER"; then
    pass "读表可用：正常输出表头且无缺失诊断（平台权限充足路径）"
else
    fail "默认调用 rc=${TOOL_RC} 行为不可解释: $(first_line)"
fi

run_sockstat
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "受限退出码语义 产物不可执行"
elif echo "${TOOL_OUT}" | grep -q "can not open file /proc/net/"; then
    if [ "${TOOL_RC}" -eq 134 ]; then
        pass "受限态 rc=134 (SIGABRT)，与上游 handle_missing_file()->abort() 语义一致"
    else
        fail "受限态 rc=${TOOL_RC}，期望 134(SIGABRT): $(first_line)"
    fi
elif [ "${TOOL_RC}" -eq 0 ]; then
    pass "读表可用态 rc=0（正常路径退出码）"
else
    fail "默认调用 rc=${TOOL_RC} 既非 0 也非 134: $(first_line)"
fi

# ── T5 读表内容校验（3 断言；读表受限时 SKIP）────────────────────────────
echo "[T5] 读表内容校验（/proc/net/{tcp,udp,raw,tcp6,udp6,raw6,unix} 解析）"
# 三条断言各自独立记账：不可执行 / /proc/net 受限时逐条 SKIP（不得合并成
# 一次，否则断言计数会随环境漂移，MANIFEST.yml 声明数就对不上了）。
run_sockstat -u
T5_OUT="${TOOL_OUT}"
if [ "${TOOL_RC}" -eq 199 ]; then
    T5_STATE="unrunnable"
elif echo "${T5_OUT}" | grep -q "can not open file /proc/net/"; then
    T5_STATE="restricted"
else
    T5_STATE="readable"
fi
T5_BODY="$(echo "${T5_OUT}" | tail -n +2 | grep -E '[[:space:]][^[:space:]]' || true)"
# 读表可用但一行 socket 都没有时，下三条断言会"空过"（对空集合做任何过滤都
# 通过）——那是无意义验证，故显式记为 SKIP 并说明原因。
if [ "${T5_STATE}" = "readable" ] && [ -z "${T5_BODY}" ]; then
    T5_STATE="no_rows"
fi

if [ "${T5_STATE}" = "unrunnable" ]; then
    skip "PROTO 列取值域 产物不可执行"
elif [ "${T5_STATE}" = "restricted" ]; then
    skip "PROTO 列取值域（/proc/net 受限，本环境无法取证）"
elif [ "${T5_STATE}" = "no_rows" ]; then
    skip "PROTO 列取值域（读表可用但无进程持有套接字，样本为空无法取证）"
else
    BADPROTO="$(echo "${T5_BODY}" | awk '{print $4}' | grep -v '^[[:space:]]*$' \
        | grep -vE '^(raw|udp4|tcp4|raw6|udp6|tcp6|unix)$' | head -3)"
    if [ -z "${BADPROTO}" ]; then
        pass "PROTO 列取值 ∈ {raw,udp4,tcp4,raw6,udp6,tcp6,unix}（protocol_to_string 契约）"
    else
        fail "PROTO 列出现契约外取值: $(echo "${BADPROTO}" | tr '\n' ' ')"
    fi
fi

if [ "${T5_STATE}" = "unrunnable" ]; then
    skip "PID 列全数字 产物不可执行"
elif [ "${T5_STATE}" = "restricted" ]; then
    skip "PID 列全数字（/proc/net 受限，本环境无法取证）"
elif [ "${T5_STATE}" = "no_rows" ]; then
    skip "PID 列全数字（读表可用但无进程持有套接字，样本为空无法取证）"
else
    BADPID="$(echo "${T5_BODY}" | awk '{print $3}' | grep -v '^[[:space:]]*$' \
        | grep -vE '^[0-9]+$' | head -3)"
    if [ -z "${BADPID}" ]; then
        pass "PID 列全为数字（/proc/<pid> 目录名解析正确）"
    else
        fail "PID 列出现非数字: $(echo "${BADPID}" | tr '\n' ' ')"
    fi
fi

if [ "${T5_STATE}" = "unrunnable" ]; then
    skip "SOURCE ADDRESS 列格式 产物不可执行"
elif [ "${T5_STATE}" = "restricted" ]; then
    skip "SOURCE ADDRESS 列格式（/proc/net 受限，本环境无法取证）"
elif [ "${T5_STATE}" = "no_rows" ]; then
    skip "SOURCE ADDRESS 列格式（读表可用但无进程持有套接字，样本为空无法取证）"
else
    # SOURCE ADDRESS 契约：IPv4/IPv6 行为 inet_ntop 产出的 addr:port（监听态
    # 端口写 *），unix 行为套接字文件绝对路径（上游 display_record 直接取
    # record->path），故两形态都属合法。
    BADADDR="$(echo "${T5_BODY}" | awk '{print $5}' | grep -v '^[[:space:]]*$' \
        | grep -vE '^/' | grep -vE '^[0-9a-fA-F:.]+:([0-9]+|\*)$' | head -3)"
    if [ -z "${BADADDR}" ]; then
        pass "SOURCE ADDRESS 列符合契约（addr:port / 监听态 addr:* / unix 绝对路径）"
    else
        fail "SOURCE ADDRESS 列既非 addr:port 也非 unix 路径: $(echo "${BADADDR}" | tr '\n' ' ')"
    fi
fi

# ── T6 上游已知缺陷取证（1 断言；与平台无关，Linux 上同样复现）──────────
# ⚠️ 必须区分两种信号崩溃，二者根因完全不同：
#   rc=139 SIGSEGV → 上游 gr_mem 的 NULL 终止项被解引用（sockstat.c:731）
#   rc=134 SIGABRT → OHOS 沙箱 /proc/net EACCES，abort() 发生在 main() 的读表
#                    阶段（sockstat.c:590-591），比 gr_mem 解引用早约 140 行，
#                    根本走不到缺陷代码——真机上不能拿它当缺陷证据。
echo "[T6] 上游 0.4.2 已知缺陷取证（按信号分流；不可解释的结局判 FAIL）"
run_sockstat -G root
if [ "${TOOL_RC}" -eq 199 ]; then
    skip "-G 组过滤 上游 NULL deref 取证 产物不可执行"
elif echo "${TOOL_OUT}" | grep -q "can not open file /proc/net/"; then
    restrict "-G 取证被 /proc/net 沙箱前置拦截（rc=${TOOL_RC} abort 发生在读表阶段，早于 gr_mem 解引用）——本环境无法证明上游缺陷，见 notes.md 源码分析"
elif [ "${TOOL_RC}" -eq 139 ]; then
    defect "-G <group> 确认上游 NULL dereference（rc=139 SIGSEGV）：grp->gr_mem 的 NULL 终止项被解引用后传给 getpwnam()，任意组均必崩；与 HarmonyOS 无关，Linux 同样复现（详见 notes.md）"
elif [ "${TOOL_RC}" -eq 0 ]; then
    defect "-G <group> 本次 rc=0 未复现上游崩溃——上游可能已修复，请复核 notes.md 与源码（此分支同样不计 FAIL，但说明取证前提已变）"
else
    fail "-G <group> rc=${TOOL_RC} 既非 SIGSEGV(139) 也非沙箱 abort，行为不可解释: $(first_line)"
fi

# ── 汇总 ─────────────────────────────────────────────────────────────────
COUNTED=$((PASS + SKIP + FAIL + RESTRICTED + DEFECT))
echo "=============================================="
echo "sockstat 0.4.2 消费者测试: ${PASS} passed, ${RESTRICTED} restricted, ${SKIP} skipped, ${DEFECT} known_upstream_defect, ${FAIL} failed  (断言计数 ${COUNTED}/${TOTAL_ASSERTIONS})"
if [ "${COUNTED}" -ne "${TOTAL_ASSERTIONS}" ]; then
    echo "FAIL: 断言计数 ${COUNTED} 与声明的 ${TOTAL_ASSERTIONS} 不一致（测试脚本与 MANIFEST.yml 脱节）"
    exit 1
fi
if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
if [ "${PASS}" -eq 0 ]; then
    echo "FAIL: 零 PASS 断言，无有效验证"
    exit 1
fi
exit 0
