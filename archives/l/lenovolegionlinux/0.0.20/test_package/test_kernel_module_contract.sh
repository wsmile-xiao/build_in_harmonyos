#!/usr/bin/env bash
# 内核模块源码契约校验（fail-closed）—— 对应上游 tests/ 中 5 个内核态用例的静态替代。
#
# 背景：lenovolegionlinux 的硬件功能全部实现在 Linux 内核模块里（Kbuild obj-m + DKMS）。
# OHOS aarch64 sysroot 没有内核构建树（无 /lib/modules/*/build、usr/src、include/generated），
# 且 legion-laptop.c 需要的 16 个内核内部头只有 5 个存在（其中 4 个是 _UAPI_ 桩）——
# 非特权用户态沙箱内无法产出可加载的 .ko。因此这里**不假装构建成功**，只做两件事：
#   1. 校验随包交付的内核模块源码确实具备内核模块契约（驱动注册 / ACPI-WMI / hwmon /
#      platform_profile / 机型 DMI 绑定），保证源码快照可用、未被裁剪；
#   2. 校验包内不存在任何预编译内核产物（.ko）与伪造状态。
# 源码缺失或契约缺失一律非 0 退出（绝不静默通过）。
#
# 用法：test_kernel_module_contract.sh <snapshot_folder>
set -euo pipefail

SNAP="${1:-}"
if [ -z "$SNAP" ] || [ ! -d "$SNAP" ]; then
    echo "[km][FAIL] usage: test_kernel_module_contract.sh <snapshot_folder>" >&2
    exit 2
fi

SRC="$SNAP/kernel_module/legion-laptop.c"
MAKEFILE="$SNAP/kernel_module/Makefile"
DKMS="$SNAP/kernel_module/dkms.conf"

[ -f "$SRC" ] || { echo "[km][FAIL] kernel module source missing: $SRC" >&2; exit 1; }
[ -s "$SRC" ] || { echo "[km][FAIL] kernel module source is empty: $SRC" >&2; exit 1; }
[ -f "$MAKEFILE" ] || { echo "[km][FAIL] kernel_module/Makefile missing" >&2; exit 1; }
[ -f "$DKMS" ] || { echo "[km][FAIL] kernel_module/dkms.conf missing" >&2; exit 1; }

ok() { echo "[km][ ok ] $1"; }
require() {
    local desc="$1" pattern="$2" file="$3"
    if grep -qF -- "$pattern" "$file"; then
        ok "$desc"
    else
        echo "[km][FAIL] $desc (pattern '$pattern' not found in $(basename "$file"))" >&2
        exit 1
    fi
}

# ── 内核模块注册契约 ──
require "module_init() present" "module_init(" "$SRC"
require "module_exit() present" "module_exit(" "$SRC"
require "MODULE_LICENSE() present" "MODULE_LICENSE(" "$SRC"

# ── 硬件接口契约（ACPI/WMI + 嵌入式控制器） ──
require "WMI hardware interface used" "wmi_" "$SRC"
require "ACPI hardware interface used" "acpi_" "$SRC"
require "DMI vendor allowlist/denylist present" "DMI_MATCH(DMI_SYS_VENDOR" "$SRC"

# ── 对外功能契约（用户态 CLI 依赖的 sysfs 面） ──
require "hwmon device registration present" "hwmon_device_register" "$SRC"
require "platform_profile registration present" "platform_profile_register" "$SRC"
require "ACPI EC path identifier present" "PNP0C09" "$SRC"

# ── 内核内部头依赖集合（OHOS sysroot 缺失 11/16 的直接来源，逐头表见 reports/） ──
# grep -c 无匹配时返回 1：计数为 0 由下一条断言处理，故此处忽略其退出码
INCLUDE_COUNT="$(grep -cE '^#include[[:space:]]*<(linux|asm)/' "$SRC" || true)"
if [ "${INCLUDE_COUNT:-0}" -lt 10 ]; then
    echo "[km][FAIL] expected >=10 kernel internal includes, found ${INCLUDE_COUNT}" >&2
    exit 1
fi
ok "kernel internal includes counted: ${INCLUDE_COUNT}"

# ── 构建系统契约（Kbuild obj-m + DKMS） ──
require "Kbuild obj-m target present" "obj-m" "$MAKEFILE"
require "Kbuild KSRC (kernel build tree) required" "KSRC" "$MAKEFILE"
require "DKMS BUILT_MODULE_NAME declared" "BUILT_MODULE_NAME" "$DKMS"

# ── 不得存在预编译内核产物 ──
# find 无结果时返回 1：空结果即通过，故此处忽略其退出码
KO="$(find "$SNAP" -name '*.ko' -print -quit 2>/dev/null || true)"
[ -z "$KO" ] || { echo "[km][FAIL] prebuilt .ko present in snapshot: $KO" >&2; exit 1; }
ok "no prebuilt .ko in the delivered snapshot"

echo "[km] kernel module source contract verified (kernel-state build/load NOT claimed)"
