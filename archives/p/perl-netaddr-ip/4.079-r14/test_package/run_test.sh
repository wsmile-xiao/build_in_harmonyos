#!/bin/bash
# run_test.sh — test_package test source (L0c compliance)
# CI L0c quality gate requires a .c/.cpp/.cc/.cxx/.sh/.py source file in test_package/.
# This wrapper enables L0c detection; actual test execution is driven by conanfile.py test().
# Usage: PERL5LIB=<pkg_dir>/lib/aarch64-linux perl test_netaddr_ip.pl
set -euo pipefail
script_dir="$(cd "$(dirname "$0")" && pwd)"
perl "${script_dir}/test_netaddr_ip.pl"
