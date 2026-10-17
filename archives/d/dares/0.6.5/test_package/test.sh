#!/bin/sh
# L1 test source file - satisfies CI L0c (test source file requirement)
# dares ships no upstream test suite; the authoritative smoke tests are
# driven by conanfile.py test(). This script mirrors the most basic check
# for shell-level runs (usage banner proves the binary links and runs).

set -e

dares 2>&1 | grep -q "DAta REScue dares 0.6.5"

echo "dares smoke test (usage banner) passed"
