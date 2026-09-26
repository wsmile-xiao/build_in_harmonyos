#!/bin/sh
# Human reproducible form of the probes in conanfile.py::test().
# LMP may be a path to the packaged binary or a PATH-resolvable command name;
# it is resolved to an absolute path below before any assertion runs.  Every call
# is bounded by timeout(1).
# Run from inside the test_package directory of the built package.
set -e
LMP="${LMP:-lmp}"
# Resolve the default / bare command name into an absolute path.  version_probe.sh
# asserts [ -f "$1" ] and the WRAP line below takes dirname(1) of this value, so a
# bare name made the three disagree: default usage (LMP unset, or "lmp" only
# reachable through PATH) aborted inside the probe with "missing packaged
# binary", a message about the harness rather than the package under test.
# Only the resolution is new -- every assertion below is unchanged, and
# conanfile.py::test() already passes an absolute path, so the conan-run arm is
# unaffected.
if [ ! -f "$LMP" ]; then
    LMP="$(command -v "$LMP" 2>/dev/null || true)"
fi
if [ ! -f "$LMP" ]; then
    echo "packaged binary not found: set LMP to the absolute path of bin/lmp" >&2
    exit 1
fi
LMP="$(CDPATH= cd -- "$(dirname -- "$LMP")" && pwd)/$(basename -- "$LMP")"
timeout 60 "$LMP" -h | grep -q "11 Feb 2026"
timeout 60 "$LMP" -h | grep -q -- "-in "
# -version must be REJECTED (rc=1); that judgement lives in version_probe.sh,
# which exits non-zero here if the binary accepts the option or hangs.
sh version_probe.sh "$LMP"
# K0 (2026-09-25): the package-named wrapper must answer --help/--version rc=0
WRAP="$(dirname "$LMP")/lammps"
timeout 60 "$WRAP" --help | grep -q "11 Feb 2026"
timeout 60 "$WRAP" --version | grep -q "20260211"
timeout 600 "$LMP" -in in.lj -log log.lammps -screen none
grep -q "Total wall time" log.lammps
grep -q "11 Feb 2026" log.lammps
echo TEST_SH_OK
