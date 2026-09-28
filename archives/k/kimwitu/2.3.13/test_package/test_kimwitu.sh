#!/bin/sh
# kimwitu (Kimwitu++) 真实调用测试：
# 1) 运行 kc++ --version（静态链接版，验证可执行）；
# 2) 用最小 kimwitu 规格 test_kimwitu.k 运行代码生成，
#    断言生成 test_kimwitu.cc/h（编译器前端产物）且内容正确。
set -euo pipefail

kc++ --version | grep -q '2.3.13'

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

cp "$(dirname "$0")/test_kimwitu.k" "$WORKDIR/"
cd "$WORKDIR"

# 真实调用：kimwitu 代码生成（Tree -> Leaf(child: Tree) 递归 phylum）
kc++ test_kimwitu.k

test -s test_kimwitu.cc
test -s test_kimwitu.h
grep -q 'translation of file' test_kimwitu.h
grep -q 'namespace kc' test_kimwitu.h

echo "kimwitu kc++ version + codegen OK"
