#!/bin/bash
# Picat configure wrapper for OpenHarmony clean-verify
# Picat uses custom Makefile (not autotools), so configure is a no-op
# The actual build is done by: cd emu && make -f Makefile.ohos

# This script is called by ohc-run.py clean-verify before make
# For makefile-based projects, configure is essentially a no-op

echo "Picat: makefile-based project, configure is no-op"
echo "Build command: cd emu && make -f Makefile.ohos"
echo "PREFIX=$1"

exit 0