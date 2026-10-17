#!/bin/sh
set -euo pipefail
# test_package consumer verification for linuxptp 4.4 (OHOS / aarch64).
#
# A downstream consumer only sees the installed package: nine binaries under
# <prefix>/bin.  Each is driven the way a user would:
#
#   * `-v`  — prints the software version (all nine support it, exit 0).
#             This is the version smoke check: it must report exactly 4.4.
#   * `-h`  — prints the usage text.  The usage line "usage: <name>" is
#             asserted for every tool.  Exit codes differ upstream: eight tools
#             return 0 while ts2phc returns -1 -> 255 (ts2phc.c:683,
#             `case 'h': usage(progname); return -1;`).  That upstream behaviour
#             is asserted explicitly rather than papered over.
#
# This is independent of the supplementary unit suite that build() links
# against the upstream objects.
export PATH="$PATH:/system/bin"

BINS="ptp4l hwstamp_ctl nsm phc2sys phc_ctl pmc timemaster ts2phc tz2alt"
VERSION="4.4"
# The one tool whose -h exits non-zero upstream (recorded, not skipped).
H_RC_255="ts2phc"
checks=0
fails=0

pass() {
	checks=$((checks + 1))
	echo "PASS: $1"
}

fail() {
	fails=$((fails + 1))
	echo "FAIL: $1"
}

echo "--- linuxptp 4.4 consumer verification ---"

for b in $BINS; do
	if command -v "$b" >/dev/null 2>&1; then
		pass "installed: $b"
	else
		fail "missing from PATH: $b"
		continue
	fi

	# version smoke check.  The exit code is captured with an if-guard so that
	# the expected non-zero -h below cannot abort the script under set -e.
	if vout=$("$b" -v 2>&1); then
		pass "$b -v exits 0"
	else
		fail "$b -v exited non-zero"
	fi
	if echo "$vout" | grep -q "$VERSION"; then
		pass "$b -v reports version $VERSION"
	else
		fail "$b -v did not report version $VERSION (got: $(echo "$vout" | head -1))"
	fi

	# usage text
	if hout=$("$b" -h 2>&1); then
		hrc=0
	else
		hrc=$?
	fi
	if echo "$hout" | grep -q "usage: $b"; then
		pass "$b -h prints 'usage: $b'"
	else
		fail "$b -h did not print its usage line"
	fi
	if [ "$b" = "$H_RC_255" ]; then
		if [ "$hrc" = "255" ]; then
			pass "$b -h exits 255 (upstream ts2phc.c:683 returns -1)"
		else
			fail "$b -h exit code changed: got $hrc, upstream returns 255"
		fi
	else
		if [ "$hrc" = "0" ]; then
			pass "$b -h exits 0"
		else
			fail "$b -h exited $hrc"
		fi
	fi
done

total=$((checks + fails))
echo "--- linuxptp 4.4 consumer checks: $checks/$total passed ---"
if [ "$fails" != "0" ]; then
	echo "RESULT: FAIL ($fails failed)"
	exit 1
fi
echo "RESULT: PASS"
exit 0
