#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the `synfig` CLI renderer
# Runs in conanrun env (PATH includes installed bin/).
# R34：真实执行被测包二进制，非空壳测试。
#
# 上游设计（tool/optionsprocessor.cpp process_trivial_info_options）：
# --version/--help 打印信息后抛 SynfigToolException(SYNFIGTOOL_HELP)，
# main() 捕获后返回退出码 3 —— 因此 --version 退出码 0 或 3 均属正常，
# 关键断言是输出必须包含真实版本号（0006 补丁修复了 "unknown" 回退）。
set -euo pipefail

echo "[test] synfig --version"
set +e
version_out=$(synfig --version 2>&1)
rc=$?
set -e
echo "exit=$rc output=$version_out"
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    echo "❌ synfig --version exited with unexpected code $rc"
    exit 1
fi
echo "$version_out" | grep -q "1.5.5" && echo "✅ --version reports 1.5.5" || {
    echo "❌ synfig --version output missing version 1.5.5: $version_out"
    exit 1
}

echo "[test] synfig --help lists render options"
# 同 --version（第 6-9 行）：上游 --help 打印后抛 SYNFIGTOOL_HELP 退出码 3。
# set -euo pipefail 下管道会以 synfig 的退出码 3 作为整体结果（pipefail 传播），
# 即使 grep 匹配成功也会走 || 误报分支 → 须先捕获输出（set +e 防 set -e 中断），
# 再对输出做 grep 断言，与第 13-25 行 --version 检查模式保持一致。
set +e
help_out=$(synfig --help 2>&1)
rc=$?
set -e
echo "exit=$rc"
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    echo "❌ synfig --help exited with unexpected code $rc"
    exit 1
fi
echo "$help_out" | grep -qiE "usage|render|synfig" && echo "✅ --help output OK" || {
    echo "❌ synfig --help output does not mention usage/render"
    exit 1
}

echo "[test] synfig binary identity (synfig-tool) in --version output"
echo "$version_out" | grep -q "synfig-tool" && echo "✅ binary identity OK" || {
    echo "❌ --version output does not identify synfig-tool: $version_out"
    exit 1
}

echo "✅ all synfig smoke checks passed"
