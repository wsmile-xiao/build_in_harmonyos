#!/usr/bin/env sh
# 该脚本是 test_package 的实质测试入口说明与 L0c 可识别源文件。
# Conan test() 执行同等命令并核验输出、负向返回码与包内容。
set -euo pipefail
mlton_bin="$1"
source_file="$2"
output_file="$3"
"$mlton_bin" -codegen c -output "$output_file" "$source_file"
"$output_file"
