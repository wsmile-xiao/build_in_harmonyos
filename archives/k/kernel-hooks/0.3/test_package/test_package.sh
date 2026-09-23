#!/bin/sh
# kernel-hooks 消费者测试（鸿蒙适配新增）
# 用法: test_package.sh <package_folder>
set -e

PKG_FOLDER="$1"
if [ -z "$PKG_FOLDER" ]; then
    echo "FAIL: package folder not provided"
    exit 1
fi

README="$PKG_FOLDER/etc/kernel-hooks.d/README"
TRIGGER="$PKG_FOLDER/share/kernel-hooks/kernel-hooks.trigger"

echo "==> Checking README ..."
[ -f "$README" ] || { echo "FAIL: README not found at $README"; exit 1; }
grep -q "kernel-hooks" "$README" || { echo "FAIL: README content mismatch"; exit 1; }

echo "==> Checking trigger script ..."
[ -f "$TRIGGER" ] || { echo "FAIL: trigger not found at $TRIGGER"; exit 1; }
[ -x "$TRIGGER" ] || { echo "FAIL: trigger not executable"; exit 1; }

echo "==> Syntax check trigger script ..."
sh -n "$TRIGGER" || { echo "FAIL: trigger syntax error"; exit 1; }

echo "==> Functional smoke test (no hooks dir) ..."
# 在无 /etc/kernel-hooks.d 的环境下，trigger 应直接 exit 0
sh "$TRIGGER" 2>/dev/null
rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: trigger exited with $rc"; exit 1; }

echo "kernel-hooks test_package: OK"
