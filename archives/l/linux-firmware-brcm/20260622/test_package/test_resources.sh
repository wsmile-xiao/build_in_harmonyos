#!/bin/bash
set -euo pipefail
# ═══════════════════════════════════════════════════════════════
# test_resources.sh — linux-firmware-brcm 20260622
# Broadcom 固件资源包验证 (25 项逐条唯一编号)
# 基于已验证的 linux-firmware-20260622.tar.xz 提取 brcm/ 目录
# SHA256: 2b9d8a358e76eb766588609135e53fa548b902c551daae33ee32f26f25e60dbb
# ═══════════════════════════════════════════════════════════════

BRCM_DIR="${1:?用法: test_resources.sh <package>/res/brcm}"
# 包根 = res/brcm 上两级（.../p/res/brcm → .../p）
PKG_ROOT="$(cd "$(dirname "$(dirname "$BRCM_DIR")")" && pwd)"
FAIL=0
PASS=0

assert() {
    local num="$1"
    local desc="$2"
    local result="$3"
    if [ "$result" = 0 ]; then
        echo "  [${num}] ✓ ${desc}"
        PASS=$((PASS+1))
    else
        echo "  [${num}] ✗ ${desc}"
        FAIL=$((FAIL+1))
    fi
}

echo "========================================================"
echo " linux-firmware-brcm 20260622 — 资源验证 (25 项断言)"
echo "========================================================"
echo ""

# ─── 1-2: 目录存在性 ───
echo "--- [目录存在性] ---"
assert "01" "res/brcm/ 目录存在" $([ -d "$BRCM_DIR" ] && echo 0 || echo 1)
assert "02" "res/brcm/ 目录非空" $([ "$(ls -A "$BRCM_DIR" 2>/dev/null | wc -l)" -gt 0 ] && echo 0 || echo 1)

# ─── 3-4: 许可证文件（真实断言：缺失/不匹配即失败）───
echo ""
echo "--- [许可证文件] ---"
# 在包内按真实路径查找许可证（licenses/ 或包根），找不到即失败，不虚构通过
LICENSE_FILE=""
for cand in "$PKG_ROOT/licenses/LICENCE.broadcom_bcm43xx" \
            "$PKG_ROOT/LICENCE.broadcom_bcm43xx" \
            "$PKG_ROOT/res/licenses/LICENCE.broadcom_bcm43xx"; do
    if [ -f "$cand" ]; then
        LICENSE_FILE="$cand"
        break
    fi
done
if [ -z "$LICENSE_FILE" ]; then
    LICENSE_FILE=$(find "$PKG_ROOT" -name "LICENCE.broadcom_bcm43xx" -type f 2>/dev/null | head -1 || true)
fi
if [ -n "$LICENSE_FILE" ] && [ -s "$LICENSE_FILE" ]; then
    LICENSE_HASH=$(sha256sum "$LICENSE_FILE" | cut -d' ' -f1)
    assert "03" "许可证文件 LICENCE.broadcom_bcm43xx 存在（$LICENSE_FILE）" 0
    assert "04" "许可证文件非空（SHA256 ${LICENSE_HASH:0:12}…）" 0
elif [ -n "$LICENSE_FILE" ]; then
    assert "03" "许可证文件 LICENCE.broadcom_bcm43xx 存在（$LICENSE_FILE）" 0
    assert "04" "许可证文件为空（证据缺失）" 1
else
    assert "03" "许可证文件 LICENCE.broadcom_bcm43xx 缺失（真实断言，无许可证证据）" 1
    assert "04" "许可证内容校验（文件缺失，无法验证 Broadcom 再分发条款）" 1
fi

# ─── 5-11: 文件存在性（抽样 7 个关键固件文件）───
echo ""
echo "--- [文件存在性 — 抽样 7 个关键固件] ---"
# 注意: brcmfmac43455-sdio.bin 和 brcmfmac43430-sdio.bin 是向上层 cypress/ 的软链接，
# brcm/ 目录内无实体文件，用 brcmfmac4330-sdio.bin 和 brcmfmac4334-sdio.bin 替代
KEY_FILES=(
    "brcmfmac4366c-pcie.bin"   # 最大固件文件 (1.1MB)
    "brcmfmac4350-pcie.bin"    # 典型 PCIe 固件 (626KB)
    "brcmfmac4330-sdio.bin"    # 常见 SDIO 固件
    "brcmfmac4334-sdio.bin"    # 常见 SDIO 固件
    "bcm43xx-0.fw"             # 传统 b43 softmac 固件
    "bcm4329-fullmac-4.bin"    # b4329 全 MAC 固件
    "BCM-0bb4-0306.hcd"        # USB 蓝牙固件
)
i=5
for f in "${KEY_FILES[@]}"; do
    n=$(printf "%02d" $i)
    assert "$n" "固件文件 '${f}' 存在" $([ -f "$BRCM_DIR/$f" ] && echo 0 || echo 1)
    i=$((i+1))
done

# ─── 12-18: 非空检查（同 7 个关键文件） ───
echo ""
echo "--- [非空检查 — 同上 7 个关键文件] ---"
i=12
for f in "${KEY_FILES[@]}"; do
    n=$(printf "%02d" $i)
    if [ -f "$BRCM_DIR/$f" ]; then
        SIZE=$(stat -c%s "$BRCM_DIR/$f" 2>/dev/null)
        assert "$n" "'${f}' 非空 (${SIZE} bytes)" $([ "$SIZE" -gt 0 ] && echo 0 || echo 1)
    else
        assert "$n" "'${f}' 非空 (文件缺失)" 1
    fi
    i=$((i+1))
done

# ─── 19-22: SHA256 逐文件校验（抽样 4 个固件） ───
echo ""
echo "--- [SHA256 逐文件校验 — 抽样 4 个固件] ---"
# 以下 SHA256 来自已验证的 linux-firmware-20260622.tar.xz
# brcmfmac43455-sdio.bin 是向上层 cypress/ 的软链接，brcm/ 内无实体，不在此校验
declare -A FILE_HASHES=(
    ["bcm43xx-0.fw"]="24668c702e723d2b1caebda047ee975ce16d7edf23788bc447dc12bcaf246b0f"
    ["bcm4329-fullmac-4.bin"]="ee87d73bc8b54aa29e343490297ca1294f71a1a4f66c845e6b301770c94082ee"
    ["brcmfmac4330-sdio.bin"]="69ee0e9b9a4233b320cdfdd935853cdf2fbd84ff6ec42f8ec572f2f0a19975a7"
    ["brcmfmac4366c-pcie.bin"]="a250275c81c626de4379591d367624b7d9da99a665a946738e657217a9d9e53e"
)
i=19
for f in "${!FILE_HASHES[@]}"; do
    n=$(printf "%02d" $i)
    if [ -f "$BRCM_DIR/$f" ]; then
        ACTUAL_HASH=$(sha256sum "$BRCM_DIR/$f" | cut -d' ' -f1)
        EXPECTED_HASH="${FILE_HASHES[$f]}"
        if [ "$ACTUAL_HASH" = "$EXPECTED_HASH" ]; then
            assert "$n" "'${f}' SHA256 匹配 (${ACTUAL_HASH:0:16}...)" 0
        else
            assert "$n" "'${f}' SHA256 不匹配 (期望 ${EXPECTED_HASH:0:16}..., 实际 ${ACTUAL_HASH:0:16}...)" 1
        fi
    else
        assert "$n" "'${f}' SHA256 校验 (文件缺失)" 1
    fi
    i=$((i+1))
done

# ─── 23: 无 ELF 文件检查 ───
echo ""
echo "--- [ELF/可执行文件检查] ---"
ELF_COUNT=$(find "$BRCM_DIR" -maxdepth 1 -type f -exec file {} \; 2>/dev/null | grep -c "ELF" || true)
EXEC_COUNT=$(find "$BRCM_DIR" -maxdepth 1 -type f -executable 2>/dev/null | wc -l)
assert "23" "无 ELF 文件 (ELF count = ${ELF_COUNT})" $([ "$ELF_COUNT" -eq 0 ] 2>/dev/null && echo 0 || echo 1)

# ─── 24: 文件总数统计 ───
echo ""
echo "--- [文件总数与类型分布] ---"
TOTAL_FILES=$(find "$BRCM_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l)
TXT_COUNT=$(find "$BRCM_DIR" -maxdepth 1 -name "*.txt" -type f 2>/dev/null | wc -l)
BIN_AND_FW=$(find "$BRCM_DIR" -maxdepth 1 \( -name "*.bin" -o -name "*.fw" -o -name "*.hcd" \) -type f 2>/dev/null | wc -l)
echo "  总文件数: ${TOTAL_FILES} (预期 >= 50)"
echo "  固件文件 (.bin/.fw/.hcd): ${BIN_AND_FW}"
echo "  板级配置 (.txt): ${TXT_COUNT}"
assert "24" "文件总数 >= 50 (实际: ${TOTAL_FILES})" $([ "$TOTAL_FILES" -ge 50 ] 2>/dev/null && echo 0 || echo 1)

# ─── 25: 文件名格式（仅检查不可打印字符） ───
echo ""
echo "--- [文件名格式] ---"
NONPRINT=$(find "$BRCM_DIR" -maxdepth 1 -type f -name "*[[:cntrl:]]*" 2>/dev/null | wc -l)
assert "25" "文件名无控制字符异常 (bad count = ${NONPRINT})" $([ "$NONPRINT" -eq 0 ] && echo 0 || echo 1)

# ─── 汇总 ───
echo ""
echo "========================================================"
echo "  测试结果汇总"
echo "========================================================"
echo "  通过: ${PASS}"
echo "  失败: ${FAIL}"
echo "  总计: $((PASS+FAIL))"
echo "========================================================"

if [ "$FAIL" -gt 0 ]; then
    echo "  状态: ❌ 部分验证项失败"
    exit 1
else
    echo "  状态: ✅ 所有验证项通过"
    exit 0
fi
