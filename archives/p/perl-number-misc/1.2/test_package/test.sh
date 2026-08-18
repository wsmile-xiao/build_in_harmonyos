#!/bin/bash
set -euo pipefail
# test.sh — Number::Misc API smoke test
# Manual testing wrapper; CI test is in conanfile.py test() method
perl -MNumber::Misc -e "exit(Number::Misc::is_numeric(q{123}) ? 0 : 1)"
