#!/bin/sh
# test_adaptive_wrap.sh — adaptive-wrap 0.9 打包产物完整性验证
# 由 test_package/conanfile.py 的 test() 调用（R34 消费者验证）。
# 纯 shell 断言，不依赖 Emacs 运行时，可在 OHOS 受限环境运行。
set -u

SITE_LISP="${1:?usage: test_adaptive_wrap.sh <site-lisp-dir>}"

fail=0

# 断言 1: 核心 .el 文件存在且非空
EL_FILE="$SITE_LISP/adaptive-wrap.el"
if [ ! -f "$EL_FILE" ]; then
    echo "FAIL: $EL_FILE not found" >&2
    fail=1
elif [ "$(wc -c < "$EL_FILE")" -lt 1000 ]; then
    echo "FAIL: $EL_FILE suspiciously small ($(wc -c < "$EL_FILE") bytes)" >&2
    fail=1
else
    echo "PASS: $EL_FILE present ($(wc -c < "$EL_FILE") bytes)"
fi

# 断言 2: 包描述文件存在
PKG_EL="$SITE_LISP/adaptive-wrap-pkg.el"
if [ ! -f "$PKG_EL" ]; then
    echo "FAIL: $PKG_EL not found" >&2
    fail=1
else
    echo "PASS: $PKG_EL present"
fi

# 断言 3: 核心符号声明存在（defcustom / define-minor-mode）
for sym in adaptive-wrap-prefix-mode adaptive-wrap-extra-indent; do
    if grep -q "$sym" "$EL_FILE" 2>/dev/null; then
        echo "PASS: symbol '$sym' declared"
    else
        echo "FAIL: symbol '$sym' missing from adaptive-wrap.el" >&2
        fail=1
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "RESULT: FAIL (adaptive-wrap test_package)" >&2
    exit 1
fi
echo "RESULT: PASS (adaptive-wrap test_package)"
exit 0
