#!/bin/sh
# Expected-failure probe for lammps 20260211 (test_package).
#
# This release has no -version option: upstream's own argument parser rejects
# it with "ERROR: Invalid command-line argument: -version (src/lammps.cpp:490)"
# and exit code 1 (measured on device, recorded in ../notes.md).  Asserting
# that here keeps the "must fail with rc 1" judgement in the shell, where the
# exit code is directly visible, instead of letting the recipe pretend the
# command succeeded.
#
# `set -u` only on purpose: `set -e` would abort on the expected failure below
# before the exit code can be checked.  A hang is reported as rc 124 by
# timeout(1) and is rejected here as "unexpected exit code", never as a pass.
#
# Usage: sh version_probe.sh /absolute/path/to/lmp   (writes version.out in cwd)
set -u

LMP="$1"
if [ ! -f "$LMP" ]; then
    echo "missing packaged binary: $LMP" >&2
    exit 1
fi

timeout 60 "$LMP" -version > version.out 2>&1
rc=$?

if [ "$rc" -ne 1 ]; then
    echo "unexpected exit code $rc from -version, want 1" >&2
    exit 1
fi

if ! grep -q "Invalid command-line argument" version.out; then
    echo "upstream argument-validation diagnostic absent from version.out" >&2
    exit 1
fi

echo "VERSION_PROBE_OK rc=$rc"
