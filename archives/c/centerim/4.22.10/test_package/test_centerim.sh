#!/bin/sh
# L1 test source file — satisfies CI L0c (test source file requirement)
# R34: smoke-test the packaged centerim binary non-interactively.
set -e

# 1) --version: binary installed + runnable, prints 4.22.10
centerim --version

# 2) --help: usage listing path works
centerim --help
