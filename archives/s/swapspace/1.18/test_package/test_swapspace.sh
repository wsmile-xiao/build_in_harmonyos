#!/bin/sh
# swapspace 1.18 consumer test — real binary invocations with assertions.
#
# Usage: test_swapspace.sh <swapspace-binary> <swappath> <confdir>
#
# Swap *activation* is intentionally not exercised: it needs root, a
# CONFIG_SWAP kernel and mutates global system state.  Everything the
# binary does without side effects is asserted here — version/help
# output, option parsing, configuration file handling, the numeric range
# validators and swap-directory filesystem probing.
set -u

BIN="$1"
SWAPPATH="$2"
CONFDIR="$3"
pass=0
fail=0

ok() { pass=$((pass+1)); echo "ok - $1"; }
no() { fail=$((fail+1)); echo "NOT OK - $1"; }

# assert_rc <expected-rc> <description> <args...>
assert_rc() {
  expected="$1"; desc="$2"; shift 2
  out=$("$BIN" "$@" </dev/null 2>&1)
  rc=$?
  if [ "$rc" -eq "$expected" ]; then
    ok "$desc (rc=$rc)"
  else
    no "$desc (expected rc=$expected, got rc=$rc)"
    echo "  output: $out"
  fi
}

# assert_out <substring> <description> <args...>  (expects rc=0)
assert_out() {
  needle="$1"; desc="$2"; shift 2
  out=$("$BIN" "$@" </dev/null 2>&1)
  rc=$?
  if [ "$rc" -ne 0 ]; then
    no "$desc (rc=$rc, expected success)"
    echo "  output: $out"
  elif echo "$out" | grep -q -- "$needle"; then
    ok "$desc"
  else
    no "$desc (missing '$needle')"
    echo "  output: $out"
  fi
}

# assert_out_rc <rc> <substring> <description> <args...>
assert_out_rc() {
  want_rc="$1"; needle="$2"; desc="$3"; shift 3
  out=$("$BIN" "$@" </dev/null 2>&1)
  rc=$?
  if [ "$rc" -ne "$want_rc" ]; then
    no "$desc (expected rc=$want_rc, got rc=$rc)"
    echo "  output: $out"
  elif echo "$out" | grep -q -- "$needle"; then
    ok "$desc"
  else
    no "$desc (missing '$needle')"
    echo "  output: $out"
  fi
}

echo "# swapspace 1.18 consumer test"
echo "# binary: $BIN"
echo "# swappath: $SWAPPATH"

# 1. version banner carries the packaged version
assert_out "swapspace 1.18" "--version reports version and exit 0" --version
assert_rc 0 "--version short flag" -V

# 2. help text is produced and lists the daemon's documented options
assert_out "Dynamic swap space manager" "--help prints description" --help
assert_out "swappath" "--help documents swappath" --help
assert_out "lower_freelimit" "--help documents lower_freelimit" --help
assert_rc 0 "--help short flag" -h

# 3. inspect mode over an existing swap directory succeeds
assert_rc 0 "inspect accepts existing swap directory" -i -s "$SWAPPATH"

# 4. inspect mode over a missing swap directory fails with a clear message
assert_out_rc 1 "Could not get filesystem information" \
  "inspect rejects missing swap directory" -i -s "$SWAPPATH/does-not-exist"

# 5. configuration file is parsed and applied. A non-existent -c path makes
#    this hermetic: the daemon reports "Using default configuration" on
#    ENOENT, so the assertion cannot be perturbed by a real /etc/swapspace.conf.
assert_rc 0 "config file is accepted" -c "$CONFDIR/swapspace-test.conf" -i
assert_out "Using default configuration" \
  "verbose mode reports its configuration source" \
  -i -s "$SWAPPATH" -v -c "$CONFDIR/no-such-file.conf"
assert_rc 0 "quiet mode with config file" \
  -c "$CONFDIR/swapspace-test.conf" -q -i
# A different directory named only in a config file. Inspect succeeding
  # there proves the swappath is read from the config rather than from the
  # compiled-in default or from any -s flag.
assert_rc 0 "a config file's own swappath is the one probed" \
  -c "$CONFDIR/alt.conf" -i
# The compiled-in default swap directory. The literal path is asserted, not
# just the exit code: a wrong VARPREFIX yields the doubled
# /var/lib/lib/swapspace, which fails this check. swappath is built as
# VARPREFIX"/lib/swapspace", so VARPREFIX must be the *parent* directory.
assert_out_rc 1 "'/var/lib/swapspace'" \
  "compiled-in default swappath is VARPREFIX/lib/swapspace" -i

# 6. configuration errors are rejected
assert_out_rc 1 "Swap path is not absolute" \
  "relative swappath in config file is rejected" \
  -c "$CONFDIR/relative.conf" -i
assert_out_rc 1 "unknown configuration item" \
  "unknown config item is rejected" -c "$CONFDIR/unknown.conf" -i
assert_out_rc 1 "unknown configuration item" \
  "unknown command-line option is rejected" --no-such-option

# 7. numeric range validators reject out-of-range values
assert_out_rc 1 "given value too large" \
  "freetarget above 99 is rejected" -i -s "$SWAPPATH" -f 100
assert_out_rc 1 "given value too small" \
  "freetarget below 2 is rejected" -i -s "$SWAPPATH" -f 1
assert_out_rc 1 "given value too small" \
  "max_swapsize below minimum is rejected" -i -s "$SWAPPATH" -M 100

# 8. in-range numeric options are accepted together
assert_rc 0 "cooldown and elasticities accepted" \
  -i -s "$SWAPPATH" -a 10 -B 10 -C 10 -l 5 -u 95

echo "1..$((pass+fail))"
echo "# passed: $pass"
echo "# failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
