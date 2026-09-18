#!/bin/bash
# Consumer test for the GNU pies 1.9 package.
#
# Runs the installed supervisor binary as a user would and asserts observable
# behaviour: the version banner, the configuration parser (both a valid and a
# deliberately broken configuration) and the dependency-map dump.
#
# Platform note: OHOS provides no AF_UNIX sockets, so a running supervisor can
# never create its control socket and therefore cannot supervise components
# here (the upstream testsuite marks the corresponding cases as expected
# failures for the same reason). This consumer test therefore exercises the
# code paths that are usable on the platform instead of pretending the
# supervisor started.
#
# usage: bash test.sh <bindir> <workdir>
set -u
# NOTE: `set -e` is deliberately not used: the negative check below expects a
# non-zero exit code from `pies --lint` and must inspect `$?` instead of
# aborting. Every assertion goes through check() and is therefore evaluated.

BINDIR="$1"
WORKDIR="$2"
CHECKS=0

fail() { echo "FAILED: $1" >&2; exit 1; }
check() { if [ "$1" = "0" ]; then CHECKS=$((CHECKS + 1)); else fail "$2"; fi; }

PIES="$BINDIR/pies"
[ -x "$PIES" ] || fail "supervisor binary not found: $PIES"
CHECKS=$((CHECKS + 1))

# 1) version banner reports the packaged version
"$PIES" --version > "$WORKDIR/version.txt" 2>&1
check $? "pies --version exited non-zero"
grep -q "1\.9" "$WORKDIR/version.txt"
check $? "version banner does not mention 1.9"

# 2) the configuration parser accepts a valid component definition
cat > "$WORKDIR/good.conf" <<EOF
component probe {
  mode respawn;
  command "/bin/sh -c 'true'";
}
EOF
"$PIES" --lint --config-file "$WORKDIR/good.conf" </dev/null > "$WORKDIR/lint-good.log" 2>&1
check $? "pies --lint rejected a valid configuration"

# 3) ...and rejects a broken one with a diagnostic (negative check)
cat > "$WORKDIR/bad.conf" <<EOF
component probe {
  mode respawn;
  command
}
EOF
"$PIES" --lint --config-file "$WORKDIR/bad.conf" </dev/null > "$WORKDIR/lint-bad.log" 2>&1
[ $? -ne 0 ]
check $? "pies --lint accepted a syntactically broken configuration"
grep -qi "syntax error" "$WORKDIR/lint-bad.log"
check $? "broken configuration produced no syntax diagnostic"

# 4) the dependency map of a valid configuration is dumped
"$PIES" --dump-depmap --config-file "$WORKDIR/good.conf" </dev/null > "$WORKDIR/depmap.log" 2>&1
check $? "pies --dump-depmap exited non-zero"
grep -qi "dependency map" "$WORKDIR/depmap.log"
check $? "dependency map output missing"

echo "test.sh: $CHECKS checks passed"
