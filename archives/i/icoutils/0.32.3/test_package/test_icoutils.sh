#!/system/bin/sh
# Test script for icoutils - verifies installed binaries work
set -e

icotool --version | grep -q "0.32.3"
wrestool --version | grep -q "0.32.3"
echo "icoutils binary tests passed"
