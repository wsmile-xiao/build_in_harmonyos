#!/bin/bash
set -euo pipefail
# ═══════════════════════════════════════════════════════════════
# test_ovmf.sh — ovmf 0.0.202605
# AArch64 QEMU UEFI 固件资源包验证（5 项逐条唯一编号）
# 产物: QEMU_EFI.fd（bare-metal 固件映像，非宿主 ELF）
# ═══════════════════════════════════════════════════════════════

FW_DIR="${1:?用法: test_ovmf.sh <package>/res/firmware}"
# 包根 = res/firmware 上两级（.../p/res/firmware → .../p）
PKG_ROOT="$(cd "$(dirname "$(dirname "$FW_DIR")")" && pwd)"
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
echo " ovmf 0.0.202605 — 固件资源验证（5 项断言）"
echo "========================================================"
echo ""

# ─── 1: 目录存在性 ───
echo "--- [目录存在性] ---"
assert "01" "res/firmware/ 目录存在" $([ -d "$FW_DIR" ] && echo 0 || echo 1)

# ─── 2-3: 固件映像存在且非空 ───
echo ""
echo "--- [固件映像] ---"
FW_FILE="$FW_DIR/QEMU_EFI.fd"
assert "02" "QEMU_EFI.fd 存在" $([ -f "$FW_FILE" ] && echo 0 || echo 1)
if [ -f "$FW_FILE" ]; then
    SIZE=$(stat -c%s "$FW_FILE" 2>/dev/null || echo 0)
    # EDK2 AArch64 QEMU_EFI.fd 典型大小约 2MB；下限 1MB 判为非空有效产物
    assert "03" "QEMU_EFI.fd 非空且大小 >= 1MB (实际 ${SIZE} bytes)" $([ "$SIZE" -ge 1048576 ] && echo 0 || echo 1)
else
    assert "03" "QEMU_EFI.fd 非空且大小 >= 1MB (文件缺失)" 1
fi

# ─── 4: 非宿主 ELF 检查（固件是 bare-metal 映像，非宿主可执行文件）───
echo ""
echo "--- [格式特征] ---"
if [ -f "$FW_FILE" ]; then
    # 宿主 ELF 以 0x7f 'E' 'L' 'F' 开头；UEFI 固件映像非宿主 ELF
    MAGIC=$(od -An -tx1 -N4 "$FW_FILE" 2>/dev/null | tr -d ' \n')
    if [ "$MAGIC" = "7f454c46" ]; then
        assert "04" "QEMU_EFI.fd 非宿主 ELF（检测到 ELF magic）" 1
    else
        assert "04" "QEMU_EFI.fd 非宿主 ELF（前 4 字节 ${MAGIC}）" 0
    fi
else
    assert "04" "QEMU_EFI.fd 非宿主 ELF（文件缺失）" 1
fi

# ─── 5: 许可证文件（BSD-2-Clause-Patent）───
echo ""
echo "--- [许可证文件] ---"
LICENSE_FILE=""
for cand in "$PKG_ROOT/licenses/License.txt" "$PKG_ROOT/License.txt"; do
    if [ -f "$cand" ]; then
        LICENSE_FILE="$cand"
        break
    fi
done
if [ -z "$LICENSE_FILE" ]; then
    LICENSE_FILE=$(find "$PKG_ROOT" -name "License.txt" -type f 2>/dev/null | head -1 || true)
fi
if [ -n "$LICENSE_FILE" ] && [ -s "$LICENSE_FILE" ]; then
    assert "05" "许可证文件 License.txt 存在且非空（$LICENSE_FILE）" 0
else
    assert "05" "许可证文件 License.txt 存在且非空（缺失或为空）" 1
fi

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
