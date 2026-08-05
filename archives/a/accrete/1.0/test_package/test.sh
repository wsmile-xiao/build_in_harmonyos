#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the accrete executable
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the packaged binary — runs the full planet-formation
# simulation and verifies the generated New.System output.
set -eu

echo "[test] accrete functional run (planet formation simulation)"
WORKDIR=$(mktemp -d "${TMPDIR:-/data/service/hnp/tmp}/accrete-test.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

accrete > accrete-run.log 2>&1
echo "   exit=$?"

if [ ! -f New.System ]; then
    echo "FAIL: accrete did not produce New.System"
    exit 1
fi

grep -q "SYSTEM  CHARACTERISTICS" New.System || {
    echo "FAIL: New.System missing header"
    exit 1
}

PLANETS=$(grep -c "^Planet #" New.System)
echo "   generated planets: $PLANETS"

if [ -z "$PLANETS" ] || [ "$PLANETS" -lt 1 ]; then
    echo "FAIL: New.System contains no planets"
    exit 1
fi

echo "OK: accrete generated New.System with $PLANETS planets"
