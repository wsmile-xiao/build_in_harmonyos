#!/bin/sh
# L1 test source file — satisfies CI L0c (test source file requirement).
# R34: substantially exercises the CHICKEN toolchain (csi interpreter + csc compiler driver).
# Invoked by test_package/conanfile.py test() with explicit tool paths.
#
# Usage: test_chicken.sh <csi> <csc> <src.scm> <out>
#   1. csi -version            — interpreter binary runs and reports version
#   2. csc -o out src.scm      — compiler driver compiles a real Scheme program
#   3. run the compiled binary — validates factorial + string + chicken-version asserts

set -e

CSI="$1"
CSC="$2"
SRC="$3"
OUT="$4"

# 1. Interpreter runs and reports version (executes the csi binary)
"$CSI" -version

# 2. Compiler driver compiles a real Scheme program (uses csc + chicken)
"$CSC" -o "$OUT" "$SRC"

# 3. Compiled binary runs and validates factorial/string results
"$OUT"
