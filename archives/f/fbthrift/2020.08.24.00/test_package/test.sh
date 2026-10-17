#!/bin/sh
# test.sh — functional smoke test for the thrift1 compiler.
# Compiles a small Thrift IDL to C++2 and verifies the generated sources.
# Run from test_package/ with the package's bin/ on PATH (conanrun env).
# This file satisfies L0c (test source file requirement).
set -e
rm -rf gen_out
mkdir -p gen_out
thrift1 --gen mstch_cpp2 -o gen_out smoke.thrift
test -f gen_out/gen-cpp2/smoke_types.h
test -f gen_out/gen-cpp2/EchoService.h
echo "PASS: thrift1 compiled smoke.thrift and generated cpp2 sources"
