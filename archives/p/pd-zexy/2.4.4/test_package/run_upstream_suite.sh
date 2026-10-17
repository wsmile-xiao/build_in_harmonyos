#!/usr/bin/env bash
# Drive the *upstream* zexy regression suite against the packaged artefacts.
#
# The upstream suite (packaged as <pkg>/share/pd-zexy/tests + abs/) is run by its
# own tests/testrunner.sh, hosted by the real `pd` binary from the puredata
# package.  Each test patch has to answer "1" on its outlet; the runner prints a
# summary block that conanfile.py parses.
#
# usage: run_upstream_suite.sh <stage_dir> <pd_binary>
set -euo pipefail

STAGE="$1"
PD="$2"

# The OHOS target has a read-only /tmp: pd and mktemp need a writable scratch dir.
export TMPDIR="$STAGE"
export HOME="$STAGE"

LOG="$STAGE/upstream-suite.log"

# Patch arguments must be RELATIVE to $STAGE: this mirrors upstream's own
# `make check` (`find tests/*/ -name '*.pd'` run from the source root).  It
# matters: tests/absgn~/abs.pd loads an abstraction named `abs`, and with an
# *absolute* patch path pd resolves that name to the patch file itself and
# aborts with "can't load abstraction within itself" — a path-form failure, not
# a port one.
cd "$STAGE" || exit 2
PATCHES=$(find tests -mindepth 2 -name '*.pd' | sort)

# -v: one line per test, -X: patches named fail* are expected to fail (XFAIL),
# -l: dump the pd log of a failing test, -s: tolerate SKIP.
# The runner's exit status is reported, not propagated: a failing upstream test
# is a finding that conanfile.py asserts on from the log, while a *broken* run
# (missing host, unreadable patch) must still surface via set -e.
rc=0
PD="$PD" LIBDIR="$STAGE" ABSDIR="$STAGE/abs" \
    bash tests/testrunner.sh -v -Xls $PATCHES > "$LOG" 2>&1 || rc=$?
echo "testrunner_rc=$rc"

sed -n '/Testsuite summary/,$p' "$LOG"
