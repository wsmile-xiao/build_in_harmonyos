#!/bin/sh
# test_package/test_cake_autorate.sh
# Verifies cake-autorate package content is installed correctly.
#
# CI worker sandbox PATH does not contain `bash` (bash lives in
# /data/service/hnp/bin/bash). This script is invoked via
# self.run('bash test_cake_autorate.sh ...', env="conanrun"), so
# conanrun.sh sets PATH to include /data/service/hnp/bin.
set -e

BC_ROOT="${1:-}"

if [ -z "$BC_ROOT" ]; then
    echo "Usage: $0 <package_root>"
    exit 1
fi

LAUNCHER="$BC_ROOT/bin/cake-autorate.sh"
LICENSE="$BC_ROOT/share/cake-autorate/LICENCE.md"

# 1. Main script exists
if [ ! -f "$LAUNCHER" ]; then
    echo "FAIL: cake-autorate.sh not found at $LAUNCHER"
    exit 1
fi

# 2. All 4 scripts exist
for s in cake-autorate.sh cake-autorate-setup.sh cake-autorate-config.sh cake-autorate; do
    if [ ! -f "$BC_ROOT/bin/$s" ]; then
        echo "FAIL: script $s not found"
        exit 1
    fi
done

# 3. R34 实质校验: bash -n 语法检查所有安装脚本
SCRIPT_COUNT=0
FAIL_COUNT=0
for s in cake-autorate.sh cake-autorate-setup.sh cake-autorate-config.sh cake-autorate; do
    SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
    if ! bash -n "$BC_ROOT/bin/$s" 2>/dev/null; then
        echo "FAIL: syntax error in $s"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "FAIL: $FAIL_COUNT script(s) failed bash -n syntax check"
    exit 1
fi

# 4. LICENCE.md exists
if [ ! -f "$LICENSE" ]; then
    echo "FAIL: LICENCE.md not found at $LICENSE"
    exit 1
fi

echo "PASS: cake-autorate package verified ($SCRIPT_COUNT scripts, syntax OK)"
