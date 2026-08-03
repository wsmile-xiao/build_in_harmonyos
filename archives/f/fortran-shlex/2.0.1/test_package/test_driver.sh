#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 7 ]; then
    echo "usage: test_driver.sh <flang> <clang> <runtime-lib> <decimal-lib> <include-dir> <lib-dir> <build-dir>" >&2
    exit 2
fi

fc=$1
cc=$2
fortran_runtime=$3
fortran_decimal=$4
include_dir=$5
lib_dir=$6
build_dir=$7
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test_object="$build_dir/test_fortran_shlex.o"
test_binary="$build_dir/test_fortran_shlex"

mkdir -p "$build_dir"
"$fc" -O2 -I"$include_dir" \
    "$script_dir/test_fortran_shlex.f90" \
    -c -o "$test_object"
"$cc" "$test_object" -L"$lib_dir" -lfortran-shlex \
    "$fortran_runtime" "$fortran_decimal" -lm -o "$test_binary"
"$test_binary"
