#!/bin/sh
# test_package runner for libkdcraw 26.04.0 (OHOS).
#
# Why this wrapper exists:
# 1. ctest's ENVIRONMENT property replaces the whole test process
#    environment, dropping the conan-provided loader path.
# 2. The consumer test links libKDcrawQt6.so, libraw*.so and libQt6*.so
#    from the conan cache; the OHOS musl loader needs LD_LIBRARY_PATH
#    covering every dependency lib dir.
#
# The wrapper prints diagnostics then execs the test binary so the exit
# code propagates to ctest.
set -u

LKD_TEST_LIB_DIRS="${LKD_TEST_LIB_DIRS:-}"

if [ -n "$LKD_TEST_LIB_DIRS" ]; then
    LD_LIBRARY_PATH="$LKD_TEST_LIB_DIRS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export LD_LIBRARY_PATH
fi

QT_QPA_PLATFORM=offscreen
export QT_QPA_PLATFORM

# Diagnostics (stdout goes into the conan create log / LastTest.log).
echo "[run_test.sh] cwd=$(pwd)"
echo "[run_test.sh] LKD_TEST_LIB_DIRS=$LKD_TEST_LIB_DIRS"

exec "$@"
