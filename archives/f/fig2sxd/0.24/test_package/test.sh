#!/usr/bin/env sh
set -eu

# fig2sxd test_package 测试脚本
# 用法: test.sh <fig2sxd 完整路径> <smalltext.fig 路径>
# 验证: 产物存在性 + smalltext.fig 转换输出 sxd 的 zip 头（PK）

fig2sxd=${1:?fig2sxd path is required}
fig_file=${2:?fig input path is required}
out_file=${3:-/tmp/fig2sxd_test_out.sxd}

# 产物存在性检查
if [ ! -f "$fig2sxd" ]; then
    echo "FAIL: fig2sxd not found at $fig2sxd" >&2
    exit 1
fi
echo "PASS: fig2sxd exists at $fig2sxd"

# 输入文件检查
if [ ! -f "$fig_file" ]; then
    echo "FAIL: fig input not found at $fig_file" >&2
    exit 1
fi

# 转换验证：fig2sxd 输出 .sxd 为 zip 压缩格式，文件头应为 PK
"$fig2sxd" -w "$fig_file" "$out_file"
if [ -f "$out_file" ]; then
    header=$(od -An -N2 -c "$out_file" | tr -d ' \n')
    if [ "$header" = "PK" ]; then
        echo "PASS: sxd output zip header (PK) OK"
        rm -f "$out_file"
    else
        echo "FAIL: unexpected sxd output header: $header" >&2
        rm -f "$out_file"
        exit 1
    fi
else
    echo "FAIL: sxd output not created at $out_file" >&2
    exit 1
fi

echo "PASS: fig2sxd conversion verified successfully"
