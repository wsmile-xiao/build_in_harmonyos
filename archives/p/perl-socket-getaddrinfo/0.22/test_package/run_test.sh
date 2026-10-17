#!/bin/sh
# Test wrapper for perl-socket-getaddrinfo
# CI L0c recognizes .sh as test source file; conanfile.py test() calls this script.
# Usage: run_test.sh <PERL5LIB_PATH>
#   PERL5LIB_PATH: colon-separated Perl library paths (set by conanfile.py test())
PERL5LIB="${1:-$PERL5LIB}" perl "$(dirname "$0")/test_getaddrinfo.pl"
