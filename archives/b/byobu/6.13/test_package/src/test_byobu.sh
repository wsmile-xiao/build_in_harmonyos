#!/bin/sh
# Test byobu installation integrity
# Verifies that byobu scripts and resources are properly installed
set -e

PREFIX="${1:-${BYOBU_PREFIX:-/usr/local}}"

# Verify byobu binary exists and is executable
test -f "$PREFIX/bin/byobu"
test -x "$PREFIX/bin/byobu"
head -1 "$PREFIX/bin/byobu" | grep -q '^#!.*sh'

# Verify library includes
test -f "$PREFIX/lib/byobu/include/common"
test -f "$PREFIX/lib/byobu/include/colors"
test -f "$PREFIX/lib/byobu/include/constants"
test -f "$PREFIX/lib/byobu/include/dirs"

# Verify symlinks
test -L "$PREFIX/bin/byobu-screen"
test -L "$PREFIX/bin/byobu-tmux"

# Verify shared resources
test -f "$PREFIX/share/byobu/status/status"
test -f "$PREFIX/etc/byobu/backend"

echo "test_byobu.sh: all checks passed"
