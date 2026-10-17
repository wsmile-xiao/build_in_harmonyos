#!/bin/sh
# test_package/test.sh — smoke test for the zsync executables.
#
# zsync 0.6.3 only implements the short -V flag; --version and --help are not
# recognised (zsync exits 3, zsyncmake silently builds a .zsync from stdin into
# stdout), so -V is the only supported way to confirm the tools run.
set -eu

zsync -V </dev/null >/dev/null
zsyncmake -V </dev/null >/dev/null

echo "zsync command smoke ok"
