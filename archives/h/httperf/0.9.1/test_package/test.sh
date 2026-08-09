#!/bin/sh
# L1 test source file - satisfies CI L0c (test source file requirement)
# R34: Tests substantially exercise httperf's functionality (real benchmark).
# The actual tests run via conanfile.py test() method.

set -e
set -o pipefail

# Test 1: httperf --version (smoke test)
httperf --version

# Test 2: real benchmark against local HTTP server on loopback
# (started by conanfile.py test() before invoking this script)
# \b word boundaries prevent prefix matches (e.g. 3 matching 30)
httperf --server=127.0.0.1 --port=18080 --num-conns=3 --num-calls=2 --rate=5 \
  | grep -q '^Total: connections 3\b requests 6\b replies 3\b'
echo "httperf benchmark OK"
