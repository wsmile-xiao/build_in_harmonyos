#!/bin/sh
# test.sh — ngspice test: verify the binary runs and reports version
ngspice --version 2>&1 | grep -q "ngspice-42" && echo "PASS: ngspice --version shows correct version" || { echo "FAIL: ngspice --version did not show expected output"; exit 1; }
