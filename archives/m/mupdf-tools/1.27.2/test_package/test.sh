#!/bin/sh
# Test: verify mutool binary runs and reports version
# This is the L0c test source file required by CI
mutool -v 2>&1 | grep -q "1.27.2" || { echo "FAIL: mutool not working"; exit 1; }
echo "PASS: mutool reports version 1.27.2"
