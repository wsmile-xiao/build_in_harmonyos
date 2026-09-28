#!/usr/bin/env bash
# Consumer test driver for the packaged gcc-c-fortran toolchain.
#
# Compiles and runs a real Fortran 90 program with the packaged gfortran,
# exercising double-precision arithmetic, array intrinsics and formatted I/O
# through the libgfortran runtime.  Satisfies the L0c test-source gate
# (test_package must contain a .sh/.c/.cpp test source) and R34 (the test
# genuinely exercises the packaged binaries).
#
# Usage: test_driver.sh <gfortran> <source.f90> <outdir>
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "usage: test_driver.sh <gfortran> <source.f90> <outdir>" >&2
    exit 2
fi

gfortran=$1
source_f90=$2
outdir=$3

if [ ! -x "$gfortran" ]; then
    echo "gfortran not found or not executable: $gfortran" >&2
    exit 1
fi
if [ ! -f "$source_f90" ]; then
    echo "Fortran test source not found: $source_f90" >&2
    exit 1
fi

mkdir -p "$outdir"
binary="$outdir/fortran_test"

"$gfortran" --version >/dev/null
"$gfortran" -O2 -ffree-line-length-none "$source_f90" -o "$binary"
"$binary"
