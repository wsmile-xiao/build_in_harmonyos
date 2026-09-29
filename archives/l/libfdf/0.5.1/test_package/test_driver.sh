#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 8 ]; then
    echo "usage: test_driver.sh <flang> <clang> <runtime-lib> <decimal-lib> <include-dir> <lib-dir> <build-dir> <source-dir>" >&2
    exit 2
fi

fc=$1
cc=$2
fortran_runtime=$3
fortran_decimal=$4
include_dir=$5
lib_dir=$6
build_dir=$7
source_dir=$8

test_object="$build_dir/test_libfdf.o"
test_binary="$build_dir/test_libfdf"

mkdir -p "$build_dir"
cp "$source_dir/test.fdf" "$build_dir/test.fdf"

"$fc" -O2 -I"$include_dir" \
    "$source_dir/test_libfdf.f90" \
    -c -o "$test_object"

"$cc" "$test_object" -L"$lib_dir" -lfdf \
    "$fortran_runtime" "$fortran_decimal" -lm -o "$test_binary"

sign_tool=/data/service/hnp/bin/binary-sign-tool
objcopy=/data/service/hnp/bin/llvm-objcopy
if [ -x "$sign_tool" ]; then
    "$objcopy" --remove-section .codesign "$test_binary" 2>/dev/null || true
    "$sign_tool" sign -inFile "$test_binary" -outFile "$test_binary" -selfSign 1
fi
chmod 0755 "$test_binary"

cd "$build_dir"
"$test_binary"
