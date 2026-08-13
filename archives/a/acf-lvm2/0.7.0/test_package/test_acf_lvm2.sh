#!/bin/sh
# test_acf_lvm2.sh — L1 test for acf-lvm2 0.7.0
# Verifies the packaged pure-Lua ACF lvm2 module:
#   1. Required files exist (controller, model, menu, roles, view templates)
#   2. Package layout matches ACF convention (share/acf/app/lvm2/)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-lvm2 package root.
# Priority 1: ACF_LVM2_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for lvm2-controller.lua.
APP_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_LVM2_PKG_ROOT:-}" ] && [ -d "${ACF_LVM2_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_LVM2_PKG_ROOT}"
    APP_DIR="${PKG_ROOT}/usr/share/acf/app/lvm2"
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for lvm2-controller.lua
if [ -z "$APP_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/lvm2/lvm2-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            APP_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/lvm2/lvm2-controller.lua$||')
        fi
    fi
fi

if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR" ]; then
    echo "  ❌ 未找到 acf-lvm2 包布局 (usr/share/acf/app/lvm2/)"
    exit 1
fi

echo "测试 acf-lvm2 0.7.0 包布局: $APP_DIR"

# ── Required files ──
for f in lvm2-controller.lua lvm2-model.lua lvm2.menu lvm2.roles lvm2-details-html.lsp; do
    if [ -f "$APP_DIR/$f" ]; then
        ok "文件存在: $f"
    else
        no "文件缺失: $f"
    fi
done

# ── Summary ──
echo ""
echo "结果: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "  ❌ acf-lvm2 test_package 失败"
    exit 1
else
    echo "  ✅ acf-lvm2 test_package 通过"
    exit 0
fi
