#!/bin/sh
# test_package/run_test.sh — L0c-compliant runner for ceni 2.33.
# CI L0c only counts *.{c,cpp,cc,cxx,sh,py} as test sources, so the real
# consumer test (test_ceni.pl, 6 Test::More assertions on Ceni::Backend)
# needs this .sh wrapper. Usage: run_test.sh <perl> <lib_dir> <script>
set -eu

PERL_BIN="${1:?usage: run_test.sh <perl> <lib_dir> <script>}"
LIB_DIR="${2:?usage: run_test.sh <perl> <lib_dir> <script>}"
SCRIPT="${3:?usage: run_test.sh <perl> <lib_dir> <script>}"

exec "$PERL_BIN" "-I$LIB_DIR" "$SCRIPT"
