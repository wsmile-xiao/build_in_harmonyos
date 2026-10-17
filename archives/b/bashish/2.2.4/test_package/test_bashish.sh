#!/bin/sh
# test_package/test_bashish.sh
# Verifies bashish package content is installed correctly.
#
# CI worker sandbox PATH does not contain `bash` (bash lives in
# /data/service/hnp/bin/bash). This script is invoked via
# self.run('bash test_bashish.sh ...', env="conanrun"), so conanrun.sh
# sets PATH to include /data/service/hnp/bin. All `bash` calls below
# rely on that PATH — do not hardcode an absolute bash path.
set -e

BC_ROOT="${1:-}"

if [ -z "$BC_ROOT" ]; then
    echo "Usage: $0 <package_root>"
    exit 1
fi

LAUNCHER="$BC_ROOT/bin/bashish"
DATA="$BC_ROOT/share/bashish"

# 1. Launcher exists
if [ ! -f "$LAUNCHER" ]; then
    echo "FAIL: launcher not found at $LAUNCHER"
    exit 1
fi

# 2. Theme-data tree exists
if [ ! -d "$DATA" ]; then
    echo "FAIL: share/bashish/ not found at $DATA"
    exit 1
fi

# 3. R34 实质校验: bash -n 语法检查 launcher
bash -n "$LAUNCHER"

# 4. R34 实质校验: bash -n 语法检查所有安装的 .sh 脚本
SCRIPT_COUNT=0
FAIL_COUNT=0
for sh in $(find "$DATA" -name "*.sh" -type f 2>/dev/null); do
    SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
    if ! bash -n "$sh" 2>/dev/null; then
        echo "FAIL: syntax error in $sh"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "FAIL: $FAIL_COUNT script(s) failed bash -n syntax check"
    exit 1
fi

# 5. Expected subdirectories present
for sub in main themes lib defaults; do
    if [ ! -d "$DATA/$sub" ]; then
        echo "FAIL: expected subdirectory $sub/ not found at $DATA/$sub"
        exit 1
    fi
done

echo "PASS: bashish package verified ($SCRIPT_COUNT scripts, launcher syntax OK)"
