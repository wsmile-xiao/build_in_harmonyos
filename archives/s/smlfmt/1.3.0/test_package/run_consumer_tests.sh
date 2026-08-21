#!/usr/bin/env sh
# 该脚本是 test_package 的实质测试入口说明与 L0c 可识别源文件。
# Conan test() 执行同等命令并核验输出、负向返回码与包内容。
set -euo pipefail

smlfmt_bin="$1"
source_dir="$(dirname "$0")"

# Consumer test: parse a well-formatted SML file
"$smlfmt_bin" --preview-only --safety-check "$source_dir/good.sml"
echo "CONSUMER_TEST: parse good.sml PASS"

# Negative test: invalid SML must be rejected (non-zero exit)
if "$smlfmt_bin" --preview-only --safety-check "$source_dir/bad.sml" 2>/dev/null; then
    echo "ERROR: bad.sml should have been rejected" >&2
    exit 1
fi
echo "NEGATIVE_TEST: bad.sml rejected PASS"

# Format check test: unformatted file must be detected (non-zero exit)
if "$smlfmt_bin" --check "$source_dir/unformatted.sml" 2>/dev/null; then
    echo "ERROR: unformatted.sml should have been detected as needing format" >&2
    exit 1
fi
echo "FORMAT_CHECK_TEST: unformatted.sml detected PASS"
