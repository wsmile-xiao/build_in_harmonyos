#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the vgrabbj CLI executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
#
# vgrabbj -V prints the version and exits 0 (a real linked, executable check).
# We capture its runtime output and also assert it is non-empty: an exit-0
# passer that prints nothing (e.g. a broken/empty binary) must be caught, not
# counted as a pass (per HMBS falsification rule: verify the output is real,
# not just the return code).
#
# IMPORTANT stream note: upstream src/v_config.c opt_version handler does
#   fprintf(stderr, "%s %s\n", option, VERSION); exit(0);
# i.e. the version string is written to STDERR, not stdout. We must therefore
# merge 2>&1 when capturing, otherwise "$(vgrabbj -V)" captures only stdout
# (which is empty) and the empty-output assertion false-fails a healthy binary.
# NOTE: don't use `--help`/`-h` — upstream src/v_config.c usage() always ends
# with exit(1), so --help/-h return exit code 1 by design. -V (opt_version)
# is the correct, device-free, exit-0 verification command.
set -euo pipefail

echo "[test] vgrabbj -V (print version to stderr and exit 0)"
VERSION_OUT="$(vgrabbj -V 2>&1)"
echo "$VERSION_OUT"

if [ -z "$VERSION_OUT" ]; then
    echo "❌ vgrabbj -V produced empty output (binary may be broken)"
    exit 1
fi
echo "✅ vgrabbj -V returned exit 0 with non-empty version output"
