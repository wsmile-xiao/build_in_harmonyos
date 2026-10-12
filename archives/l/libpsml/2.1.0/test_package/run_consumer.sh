#!/bin/sh
# run_consumer.sh -- L0c POSIX wrapper for the Fortran consumer test.
#
# CI L0c only recognises *.c/*.cpp/*.cc/*.cxx/*.sh/*.py under test_package/
# as test sources, so a pure-Fortran consumer (*.f90) alone fails the gate
# with no_test_sources. This is a thin pass-through: it takes the already
# linked consumer binary + fixture + log path and execs the real test.
# No assertions live here; the count source stays the Fortran program's
# own summary line "LIBPSML_CONSUMER N/M CHECKS PASSED" parsed by
# test_package/conanfile.py (no stdout word counting, no arithmetic fixups).
#
# Usage: run_consumer.sh <binary> <fixture> <log>
set -eu
if [ "$#" -ne 3 ]; then
  echo "usage: run_consumer.sh <binary> <fixture> <log>" >&2
  exit 2
fi
binary="$1"
fixture="$2"
log="$3"
if [ ! -x "$binary" ]; then
  echo "run_consumer.sh: not executable: $binary" >&2
  exit 1
fi
if [ ! -s "$fixture" ]; then
  echo "run_consumer.sh: fixture empty or missing: $fixture" >&2
  exit 1
fi
exec "$binary" "$fixture" > "$log" 2>&1
