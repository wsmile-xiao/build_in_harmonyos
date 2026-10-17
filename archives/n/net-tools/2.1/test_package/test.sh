#!/bin/bash
# test_package/test.sh -- net-tools 2.1 消费者测试（36 断言）
# T1: 12 个工具存在且为合法 aarch64 ELF（magic + e_machine）
# T2: 核心工具真机实跑：ifconfig -a / netstat -rn / route -n / hostname / arp -n
# T3: 其余 7 个工具实跑（rc=0 或输出非空诊断/usage）
# T4: 12 个工具 --version 全量验证
# 交叉编译环境（CI worker）产物不可执行 → 该条按 SKIP 计（仅确认 ELF 合法）；
# 真机上"能执行但失败"是硬 FAIL，不掩盖。
# 例外（平台受限 RESTRICTED）：rc!=0 且输出含 "Permission denied"——OHOS 沙箱
# 权限模型下普通 uid 无权读 /proc/net/{route,arp}（Linux 上这些文件世界可读，
# 普通用户 netstat -rn 合法），工具正确解析参数并如实报告 EACCES，行为与
# Linux 一致，按平台受限计，不计 FAIL；其余任何非零 rc 仍为硬 FAIL。
set -u

PATH_DIRS=$(echo "${PATH}" | tr ':' '\n')
PKG_BIN=""
PKG_SBIN=""
for d in ${PATH_DIRS}; do
    [ -n "${d}" ] || continue
    if [ -f "${d}/netstat" ] && [ -z "${PKG_BIN}" ]; then PKG_BIN="${d}"; fi
    if [ -f "${d}/mii-tool" ] && [ -z "${PKG_SBIN}" ]; then PKG_SBIN="${d}"; fi
done
echo "[test] package bin  dir: ${PKG_BIN}"
echo "[test] package sbin dir: ${PKG_SBIN}"

if [ -z "${PKG_BIN}" ] || [ -z "${PKG_SBIN}" ]; then
    echo "FAIL: net-tools package dirs not found on conanrun PATH"
    exit 1
fi

# 合法 aarch64 ELF 校验（magic 0x7f 'E' 'L' 'F' + e_machine==183 aarch64，无需 readelf）
is_aarch64_elf() {
    local f="$1"
    [ -f "$f" ] || return 1
    if command -v od >/dev/null 2>&1; then
        local magic mach
        magic=$(dd if="$f" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')
        [ "$magic" = "7f454c46" ] || return 1
        # e_machine little-endian at offset 18-19: aarch64 = 0xB7 0x00
        mach=$(dd if="$f" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
        [ "$mach" = "b700" ]
    else
        # 无 od 环境：退化为仅校验 magic
        local head4
        head4=$(dd if="$f" bs=1 count=4 2>/dev/null | tr -d '\0')
        [ "$head4" = "ELF" ]
    fi
}

BIN_TOOLS="ifconfig netstat route hostname"
SBIN_TOOLS="nameif arp rarp iptunnel ipmaddr mii-tool plipconfig slattach"

PASS=0
SKIP=0
FAIL=0
RESTRICTED=0

pass() { echo "OK: $1"; PASS=$((PASS + 1)); }
skip() { echo "SKIP: $1"; SKIP=$((SKIP + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
restrict() { echo "RESTRICTED: $1"; RESTRICTED=$((RESTRICTED + 1)); }

TOOL_RC=0
TOOL_OUT=""

# run_tool exe [args...]：执行并把 rc/输出存入 TOOL_RC/TOOL_OUT；
# 产物在本环境不可执行（交叉编译场景）时 TOOL_RC=199。
run_tool() {
    local exe="$1"; shift
    TOOL_OUT=$("$exe" "$@" 2>&1)
    TOOL_RC=$?
    case "${TOOL_OUT}" in
        *"Exec format error"*|*"cannot execute"*) TOOL_RC=199 ;;
    esac
    if [ "${TOOL_RC}" -eq 126 ] || [ "${TOOL_RC}" -eq 127 ]; then TOOL_RC=199; fi
}

first_line() { printf '%s' "${TOOL_OUT}" | sed -n '1p' | cut -c1-80; }

echo "[T1] 12 个工具存在且为合法 aarch64 ELF"
check_elf() {
    local exe="$1"
    local name; name=$(basename "${exe}")
    if [ -f "${exe}" ] && is_aarch64_elf "${exe}"; then
        pass "${name} 合法 aarch64 ELF"
    else
        fail "${name} 缺失或非合法 aarch64 ELF"
    fi
}
for t in ${BIN_TOOLS}; do check_elf "${PKG_BIN}/${t}"; done
for t in ${SBIN_TOOLS}; do check_elf "${PKG_SBIN}/${t}"; done

echo "[T2] 核心工具真机实跑（查询真实系统状态）"
# ifconfig -a：列出全部接口
run_tool "${PKG_BIN}/ifconfig" -a
if [ "${TOOL_RC}" -eq 199 ]; then skip "ifconfig -a 产物不可执行（交叉编译环境）"
elif [ "${TOOL_RC}" -eq 0 ] && (echo "${TOOL_OUT}" | grep -qE 'flags=|HWaddr|mtu'); then
    pass "ifconfig -a 列出接口: $(first_line)"
else fail "ifconfig -a rc=${TOOL_RC}: $(first_line)"; fi

# netstat -rn：内核路由表
run_tool "${PKG_BIN}/netstat" -rn
if [ "${TOOL_RC}" -eq 199 ]; then skip "netstat -rn 产物不可执行（交叉编译环境）"
elif [ "${TOOL_RC}" -eq 0 ] && (echo "${TOOL_OUT}" | grep -qE 'Kernel IP routing table|Destination'); then
    pass "netstat -rn 输出路由表: $(first_line)"
elif echo "${TOOL_OUT}" | grep -q "Permission denied"; then
    restrict "netstat -rn 平台受限（OHOS /proc/net/route 权限拒绝）: $(first_line)"
else fail "netstat -rn rc=${TOOL_RC}: $(first_line)"; fi

# route -n：路由表
run_tool "${PKG_BIN}/route" -n
if [ "${TOOL_RC}" -eq 199 ]; then skip "route -n 产物不可执行（交叉编译环境）"
elif [ "${TOOL_RC}" -eq 0 ] && [ -n "${TOOL_OUT}" ]; then
    pass "route -n 输出路由表: $(first_line)"
elif echo "${TOOL_OUT}" | grep -q "Permission denied"; then
    restrict "route -n 平台受限（OHOS /proc/net/route 权限拒绝）: $(first_line)"
else fail "route -n rc=${TOOL_RC}: $(first_line)"; fi

# hostname：本机名
run_tool "${PKG_BIN}/hostname"
if [ "${TOOL_RC}" -eq 199 ]; then skip "hostname 产物不可执行（交叉编译环境）"
elif [ "${TOOL_RC}" -eq 0 ] && [ -n "${TOOL_OUT}" ]; then
    pass "hostname 输出: $(first_line)"
else fail "hostname rc=${TOOL_RC}: $(first_line)"; fi

# arp -n：ARP 表（空表合法）
run_tool "${PKG_SBIN}/arp" -n
if [ "${TOOL_RC}" -eq 199 ]; then skip "arp -n 产物不可执行（交叉编译环境）"
elif [ "${TOOL_RC}" -eq 0 ]; then
    pass "arp -n 执行成功（表可能为空）: $(first_line)"
elif echo "${TOOL_OUT}" | grep -q "Permission denied"; then
    restrict "arp -n 平台受限（OHOS /proc/net/arp 权限拒绝）: $(first_line)"
else fail "arp -n rc=${TOOL_RC}: $(first_line)"; fi

echo "[T3] 其余 7 个工具实跑（rc=0 或输出非空诊断）"
check_run_diag() {
    local exe="$1"; local name; name=$(basename "${exe}")
    run_tool "${exe}"
    if [ "${TOOL_RC}" -eq 199 ]; then skip "${name} 产物不可执行（交叉编译环境）"
    elif [ "${TOOL_RC}" -eq 0 ] || [ -n "${TOOL_OUT}" ]; then
        pass "${name} 执行（rc=${TOOL_RC}）: $(first_line)"
    else fail "${name} rc=${TOOL_RC} 且无输出"; fi
}
for t in nameif rarp iptunnel ipmaddr mii-tool plipconfig slattach; do
    check_run_diag "${PKG_SBIN}/${t}"
done

echo "[T4] 12 个工具 --version 全量验证"
check_version() {
    local exe="$1"; local name; name=$(basename "${exe}")
    run_tool "${exe}" --version
    if [ "${TOOL_RC}" -eq 199 ]; then skip "${name} --version 产物不可执行（交叉编译环境）"
    elif [ "${TOOL_RC}" -eq 0 ] && [ -n "${TOOL_OUT}" ]; then
        pass "${name} --version: $(first_line)"
    elif echo "${TOOL_OUT}" | grep -qi "usage"; then
        pass "${name} --version 打印 usage（rc=${TOOL_RC}）"
    else fail "${name} --version rc=${TOOL_RC}: $(first_line)"; fi
}
for t in ${BIN_TOOLS}; do check_version "${PKG_BIN}/${t}"; done
for t in ${SBIN_TOOLS}; do check_version "${PKG_SBIN}/${t}"; done

echo "=============================================="
echo "net-tools 消费者测试: ${PASS} passed, ${RESTRICTED} restricted, ${SKIP} skipped, ${FAIL} failed"
if [ "${FAIL}" -gt 0 ]; then exit 1; fi
if [ "${PASS}" -eq 0 ] && [ "${RESTRICTED}" -eq 0 ]; then
    echo "FAIL: 全部跳过且无平台受限判定，无有效验证（T1 ELF 校验应先通过）"
    exit 1
fi
exit 0
