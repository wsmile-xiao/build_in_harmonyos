#!/bin/sh
# wiliki 0.6.2 test_package entry (L0c: test source must be .c/.cpp/.cc/.cxx/.sh/.py).
# wiliki is a pure-Scheme library: the real assertions live in test_wiliki.scm
# (loads wiliki.parse and checks wiliki-parse-string output, R34).  This sh
# wrapper just locates gosh from the conanrun PATH and runs that script.
set -euo pipefail
DIR="$(dirname "$0")"
gosh "$DIR/test_wiliki.scm"
