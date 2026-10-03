#!/bin/bash
# test_package/test.sh -- john-jumbo 1.9.0 消费者测试（执行器结构：
# 逐例独立 TEST PASS/FAIL + 末行 TEST SUMMARY，任一失败 exit(1)）
# T1: john 存在且为合法 aarch64 ELF（magic + e_machine）+ 运行时数据文件打包完整
# T2: --list=build-info 版本/构建目标校验（1.9.0-jumbo-1 的 build-info 无
#     Arch/位宽行，架构校验用 "Build: linux-arm64le" 目标行）
# T3: --list=formats 格式注册表规模校验
# T4: 7 格式自检（--test 跑各格式内置测试向量，校验无 Self test failed）：
#     基础 5（Raw-MD5/md5crypt/sha256crypt/sha512crypt/NT）+ 依赖路径 2
#     （PKZIP→zlib；openssl-enc→OpenSSL "enc" AES-128/MD5，libcrypto）——
#     openssl/1.1.1w 与 zlib/1.3.1.1 为制品仓纯静态库、静态链入
#     （运行时 DT_NEEDED 仅 libc.so），这两个用例使依赖功能路径有真实覆盖
# T5: 5 组哈希 E2E 破解闭环（md5crypt/sha256crypt/sha512crypt/Raw-MD5/NT）
#     向量由 PC 端 openssl 3.5.5 生成；NT = MD4(UTF-16LE) 经 RFC 1320 全部公开向量校验
# 交叉编译环境（CI worker）产物不可执行 → 执行类用例逐条按 SKIP 计
# （仅确认 ELF 合法/数据打包完整）；真机上"能执行但失败"是硬 FAIL，不掩盖。
# OHOS /tmp 只读：测试工作目录一律建在 cwd（conan test 构建目录，可写）。
# 计数口径：断言数 = 具名用例数（无"汇总 PASS"行），T1×4+T2×2+T3×1+T4×7+T5×5=19；
# 交叉编译环境下执行类用例按具名用例逐条 SKIP，总数口径不变。
set -uo pipefail
# 不用 -e：用例失败经 fail() 计数、由末行 TEST SUMMARY 统一 exit(1)，
# -e 会在首个失败处提前中断，无法收集全部用例结果。

PATH_DIRS=$(echo "${PATH}" | tr ':' '\n')
PKG_BIN=""
for d in ${PATH_DIRS}; do
    [ -n "${d}" ] || continue
    if [ -f "${d}/john" ] && [ -z "${PKG_BIN}" ]; then PKG_BIN="${d}"; fi
done
echo "[test] package bin dir: ${PKG_BIN}"

if [ -z "${PKG_BIN}" ]; then
    echo "FAIL: john-jumbo package bin dir not found on conanrun PATH"
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
        mach=$(dd if="$f" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
        [ "$mach" = "b700" ]
    else
        # 无 od 回退：校验口径与 od 分支一致（magic + e_machine）。
        # 跳过 0x7f 魔数首字节、取后 3 字节比对 "ELF"（0x7f 非可打印字符，
        # 无法整 4 字节直接比较）；e_machine 取 offset 18 首字节 0xB7
        # （little-endian aarch64 = 0xB7 0x00）。dd 缺失或任一校验不通过
        # 均 return 1（fail），不误判为通过。
        command -v dd >/dev/null 2>&1 || return 1
        local m3 m1
        m3=$(dd if="$f" bs=1 skip=1 count=3 2>/dev/null | tr -d '\0')
        [ "$m3" = "ELF" ] || return 1
        m1=$(dd if="$f" bs=1 skip=18 count=1 2>/dev/null | tr -d '\0')
        [ "$m1" = "$(printf '\267')" ]
    fi
}

PASS=0
SKIP=0
FAIL=0
RESTRICTED=0

pass() { echo "TEST PASS: $1"; PASS=$((PASS + 1)); }
skip() { echo "TEST SKIP: $1"; SKIP=$((SKIP + 1)); }
fail() { echo "TEST FAIL: $1"; FAIL=$((FAIL + 1)); }
restrict() { echo "TEST RESTRICTED: $1"; RESTRICTED=$((RESTRICTED + 1)); }

TOOL_RC=0
TOOL_OUT=""

# run_john args...：执行并把 rc/输出存入 TOOL_RC/TOOL_OUT；
# 产物在本环境不可执行（交叉编译场景）时 TOOL_RC=199。
run_john() {
    TOOL_OUT=$("${PKG_BIN}/john" "$@" 2>&1)
    TOOL_RC=$?
    case "${TOOL_OUT}" in
        *"Exec format error"*|*"cannot execute"*) TOOL_RC=199 ;;
    esac
    if [ "${TOOL_RC}" -eq 126 ] || [ "${TOOL_RC}" -eq 127 ]; then TOOL_RC=199; fi
}

first_line() { printf '%s' "${TOOL_OUT}" | sed -n '1p' | cut -c1-100; }

WORK=$(pwd)/jt-work
rm -rf "${WORK}"
mkdir -p "${WORK}"
# 注：1.9.0-jumbo-1 path.c 不读 JOHN 环境变量（该支持为后续 jumbo 版本引入），
# $JOHN = dirname(argv[0])，故运行时数据须与二进制同目录打包（见配方 package()）。

echo "[T1] john 二进制与运行时数据文件打包校验"
if [ -f "${PKG_BIN}/john" ] && is_aarch64_elf "${PKG_BIN}/john"; then
    pass "john 合法 aarch64 ELF"
else
    fail "john 缺失或非合法 aarch64 ELF"
fi
# $JOHN = dirname(argv[0])（此版本不读 JOHN 环境变量）→ 数据须与二进制同目录
if [ -f "${PKG_BIN}/john.conf" ]; then
    pass "john.conf 与二进制同目录打包"
else
    fail "john.conf 缺失（须在 bin/，$JOHN 解析路径）"
fi
if [ -f "${PKG_BIN}/password.lst" ]; then
    pass "password.lst 与二进制同目录打包"
else
    fail "password.lst 缺失"
fi
# john.conf 的 .include 链引用全部 11 个 run/*.conf（dynamic_disabled/
# korelogic/hybrid/dumb16/dumb32/repeats16/repeats32/dynamic/regex_alphabets/
# dynamic_flat_sse_formats，真机实测缺 korelogic.conf 即 fopen 失败）+
# $JOHN/rules/best64.rule（<rules/...> 角括号 include），缺一即配置加载失败
NCONF=$(ls "${PKG_BIN}"/*.conf 2>/dev/null | wc -l)
if [ "${NCONF}" -eq 11 ] && [ -f "${PKG_BIN}/rules/best64.rule" ]; then
    pass "john.conf include 依赖（11 个 .conf + rules/）打包完整"
else
    fail "john.conf include 依赖缺失（.conf ${NCONF}/11）"
fi

echo "[T2] --list=build-info 版本/构建目标校验"
run_john --list=build-info
if [ "${TOOL_RC}" -eq 199 ]; then
    # 交叉编译环境产物不可执行：2 个具名用例逐条 SKIP 计数
    # （保持 T1×4+T2×2+T3×1+T4×7+T5×5=19 的计数口径）
    skip "build-info Version 校验（产物不可执行，交叉编译环境）"
    skip "build-info 构建目标 linux-arm64le（产物不可执行，交叉编译环境）"
else
    if [ "${TOOL_RC}" -eq 0 ] && echo "${TOOL_OUT}" | grep -q "Version: 1.9.0-jumbo-1"; then
        pass "build-info $(echo "${TOOL_OUT}" | grep -m1 "Version:")"
    else fail "build-info rc=${TOOL_RC}: $(first_line)"; fi

    # 1.9.0-jumbo-1 的 build-info 无 Arch/位宽行（该行为后续版本引入），
    # 以 Build 目标行做架构校验：非 arm64le 目标构建将输出不同目标名
    if echo "${TOOL_OUT}" | grep -q "Build: linux-arm64le"; then
        pass "build-info 构建目标 linux-arm64le"
    else fail "build-info 构建目标: $(first_line)"; fi
fi

echo "[T3] --list=formats 格式注册表规模"
run_john --list=formats
if [ "${TOOL_RC}" -eq 199 ]; then skip "--list=formats 产物不可执行（交叉编译环境）"
elif [ "${TOOL_RC}" -eq 0 ]; then
    # --list=formats 输出为逗号分隔清单（1.9.0-jumbo-1 无每格式一行），按逗号计名
    NFMT=$(echo "${TOOL_OUT}" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -c .)
    if [ "${NFMT}" -ge 100 ]; then
        pass "--list=formats 注册格式 ${NFMT} 个（>=100）"
    else fail "--list=formats 仅 ${NFMT} 个（<100）"; fi
else fail "--list=formats rc=${TOOL_RC}: $(first_line)"; fi

echo "[T4] 7 格式自检（--test 内置测试向量；含 zlib/OpenSSL 依赖路径）"
run_john --test --format=Raw-MD5
if [ "${TOOL_RC}" -eq 199 ]; then
    # 交叉编译环境：7 个具名用例逐条 SKIP 计数
    for F in Raw-MD5 md5crypt sha256crypt sha512crypt NT PKZIP openssl-enc; do
        skip "--test 自检 ${F}（产物不可执行，交叉编译环境）"
    done
else
    # --format 仅收单个格式名（FLG_FORMAT 无 OPT_FMT_ADD_LIST，逗号列表报
    # "Unknown ciphertext format name requested"，真机实测）→ 逐格式自检。
    # PKZIP 覆盖 zlib、openssl-enc（OpenSSL "enc" AES-128/MD5）覆盖 libcrypto；
    # 每格式 1 条具名 PASS，无汇总 PASS 行（计数口径 = 具名用例数）。
    for F in Raw-MD5 md5crypt sha256crypt sha512crypt NT PKZIP openssl-enc; do
        run_john --test --format="${F}"
        if [ "${TOOL_RC}" -ne 0 ]; then
            fail "--test 自检 ${F} rc=${TOOL_RC}: $(first_line)"
        elif echo "${TOOL_OUT}" | grep -qi "Self test failed"; then
            fail "--test 自检 ${F} 存在 Self test failed"
            echo "${TOOL_OUT}" | grep -i "Self test failed" | head -3
        elif echo "${TOOL_OUT}" | grep -q "Benchmarking: ${F}"; then
            pass "--test 自检通过 ${F}"
        else
            fail "--test 自检未覆盖格式 ${F}"
        fi
    done
fi

echo "[T5] 5 组哈希 E2E 破解闭环"
# T5 独立探测可执行性（不复用 T4 循环遗留的 TOOL_RC）：--help 在本版本 rc=0，
# 产物不可执行时 run_john 把 rc 归一到 199
run_john --help
if [ "${TOOL_RC}" -eq 199 ]; then
    # 交叉编译环境：5 个具名用例逐条 SKIP 计数
    for F in md5crypt sha256crypt sha512crypt Raw-MD5 NT; do
        skip "E2E 破解 ${F}（产物不可执行，交叉编译环境）"
    done
else
    printf '%s\n' 'harmonyos123' 'decoy-one' 'decoy-two' > "${WORK}/wl.txt"
    printf '%s\n' '$1$ohos$W2GxPJ8uCnKLHq0tgTRHM1' > "${WORK}/h-md5crypt.txt"
    printf '%s\n' '$5$ohos$vZVUzjaRadM4hX56VLAiYhPbfOS2BWBFa0JWmvg0vA0' > "${WORK}/h-sha256crypt.txt"
    printf '%s\n' '$6$ohos$i/vdZ.UMCx3QF2ADd7uvoMkfu800FtigdeZKuf1kEU.alAWhhXtDSvB.51RQYiPSFlWW256Dw2DtQteIAoDwN.' > "${WORK}/h-sha512crypt.txt"
    printf '%s\n' '6bc04c8a24b444a2131c1eb79bb685cd' > "${WORK}/h-rawmd5.txt"
    printf '%s\n' 'e72c66f7c205ac0d0b9b2dc1eb4ea0ed' > "${WORK}/h-nt.txt"

    run_crack() { # run_crack <format> <hashfile>
        local _fmt="$1" _hf="$2"
        "${PKG_BIN}/john" --nolog --pot="${WORK}/pot-${_fmt}" --format="${_fmt}" \
            --wordlist="${WORK}/wl.txt" "${_hf}" >"${WORK}/out-${_fmt}" 2>&1
        if grep -F "harmonyos123" "${WORK}/pot-${_fmt}" >/dev/null 2>&1; then
            pass "E2E 破解 ${_fmt}（pot 含密码）"
        else
            fail "E2E 破解 ${_fmt}"
            tail -5 "${WORK}/out-${_fmt}" 2>/dev/null
        fi
    }

    run_crack "md5crypt" "${WORK}/h-md5crypt.txt"
    run_crack "sha256crypt" "${WORK}/h-sha256crypt.txt"
    run_crack "sha512crypt" "${WORK}/h-sha512crypt.txt"
    run_crack "Raw-MD5" "${WORK}/h-rawmd5.txt"
    run_crack "NT" "${WORK}/h-nt.txt"
fi

echo "=============================================="
echo "TEST SUMMARY: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped, ${RESTRICTED} restricted"
if [ "${FAIL}" -gt 0 ]; then exit 1; fi
if [ "${PASS}" -eq 0 ] && [ "${RESTRICTED}" -eq 0 ]; then
    echo "TEST FAIL: 全部跳过且无平台受限判定，无有效验证（T1 ELF 校验应先通过）"
    exit 1
fi
exit 0
