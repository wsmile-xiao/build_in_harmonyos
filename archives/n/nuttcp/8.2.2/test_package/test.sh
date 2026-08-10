#!/bin/bash
set -euo pipefail
# test.sh — nuttcp 8.2.2 smoke test
# Runs the nuttcp binary with -V flag to verify version output.
nuttcp -V
