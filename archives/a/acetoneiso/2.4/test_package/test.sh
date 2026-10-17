#!/usr/bin/env bash
# test_package/test.sh — smoke test for acetoneiso executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: 实质验证被测包二进制（--help 帮助输出 + 用法说明）
set -euo pipefail

# 无显示环境：使用 offscreen 平台插件（OHOS 无 X11）
export QT_QPA_PLATFORM=offscreen

echo "[test] acetoneiso --help"
if out=$(acetoneiso --help 2>&1); then
    : # 成功，继续校验输出
else
    rc=$?
    echo "❌ acetoneiso --help exited $rc"
    exit 1
fi
# 大小写不敏感匹配（可移植性）：banner 与 usage 校验
echo "$out" | grep -qi "acetoneiso" || {
    echo "❌ --help output missing AcetoneISO banner"
    exit 1
}
echo "$out" | grep -qi "usage" || {
    echo "❌ --help output missing usage line"
    exit 1
}
echo "✅ acetoneiso --help OK"
