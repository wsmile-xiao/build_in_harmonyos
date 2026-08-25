#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Performance regression tests for --fast mode.
# Each invocation must complete within THRESHOLD seconds.
# Stdout: PASS/FAIL verdict (for wanted-results comparison).
# Stderr: full timing line (visible on terminal, not captured in actual-results).

THRESHOLD=15

_timeit() {
    # Usage: _timeit <n> <flags...>
    local n="$1"; shift
    local flags="$*"
    local t
    TIMEFORMAT='%R'
    t=$({ time seq "$n" | parallel --fast $flags echo >/dev/null 2>/dev/null; } 2>&1)
    perl -e "
my \$t = \$ARGV[0];
my \$verdict = \$t <= $THRESHOLD ? 'PASS' : sprintf('FAIL(%.2fs)', \$t);
printf STDERR \"n=%-4d flags='%-22s': %.2fs %s\n\", $n, '$flags', \$t, \$verdict;
printf        \"n=%-4d flags='%-22s': %s\n\",       $n, '$flags', \$verdict;
" -- "$t"
}

par_fast_perf_N0() {
    echo '### --fast -N0 timing n=100000'
    local THRESHOLD=12
    _timeit 100000 '-N0'
    # --tag creates per-chunk tagger awk fifos; with many small chunks
    # (buf_cap=250) this is inherently slower than no-tag.
    local THRESHOLD=45
    _timeit 100000 '-N0 --tag'
}

par_fast_perf_n1() {
    echo '### --fast timing n=1'
    _timeit 1 ''
    _timeit 1 '--tag'
    _timeit 1 '--halt never'
    _timeit 1 '--tag --halt never'
}

par_fast_perf_n10() {
    echo '### --fast timing n=10'
    _timeit 10 ''
    _timeit 10 '--tag'
    _timeit 10 '--halt never'
    _timeit 10 '--tag --halt never'
}

par_fast_perf_n100() {
    echo '### --fast timing n=100'
    _timeit 100 ''
    _timeit 100 '--tag'
    _timeit 100 '--halt never'
    _timeit 100 '--tag --halt never'
}

export -f $(compgen -A function | grep -E '^par_|^_timeit')
export THRESHOLD
# --ungroup: job stderr (timing lines) flows to terminal without being captured;
# job stdout (PASS/FAIL) is tagged and captured in actual-results.
compgen -A function | grep par_ | LC_ALL=C sort |
    parallel --timeout 1000% -j1 --tag -k --ungroup --joblog /tmp/jl-`basename $0` '{}'
