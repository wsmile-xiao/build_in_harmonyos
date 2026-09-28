#!/bin/sh
# Consumer smoke test for libjxl-tools 0.11.2 (test_package test source).
#
# Runs the installed cjxl/djxl/jxlinfo the way a real user would:
#   1) banner checks (--version)
#   2) a real PPM -> cjxl -> .jxl -> djxl -> PPM roundtrip
#   3) jxlinfo container inspection of the produced .jxl file
#
# Invoked from test_package/conanfile.py test() with the conanrun env, so the
# tools' $ORIGIN/../lib RPATH resolves against the package lib/ directory.
set -eu

cjxl --version
djxl --version

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

ppm_in="$work_dir/in.ppm"
jxl="$work_dir/out.jxl"
ppm_out="$work_dir/out.ppm"

# 4x4 RGB PPM: header + 48 raw RGB bytes (4 * 4 * 3).
{
    printf 'P6\n4 4\n255\n'
    dd if=/dev/zero bs=1 count=48 2>/dev/null
} > "$ppm_in"

cjxl "$ppm_in" "$jxl"
test -s "$jxl"

djxl "$jxl" "$ppm_out"
test -s "$ppm_out"

jxlinfo "$jxl"

echo "libjxl-tools 0.11.2 smoke: cjxl encode + djxl decode + jxlinfo inspect — OK"
