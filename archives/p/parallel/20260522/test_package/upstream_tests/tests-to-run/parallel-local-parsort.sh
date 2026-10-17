#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

setup() {
    tmp=$(mktemp)
    perl -pe 's/\n/\n\0/' >"$tmp" <<EOF
chr1	1	Sample 1
chr1	11	Sample 1
chr1	111	Sample 1
chr1	1111	Sample 1
chr1	11111	Sample 1
chr1	111111	Sample 1
chr2	1	Sample 1
chr2	22	Sample 1
chr2	111	Sample 1
chr2	2222	Sample 1
chr2	11111	Sample 1
chr2	111111	Sample 1
chr10	1	Sample 1
chr10	11	Sample 1
chr10	111	Sample 1
chr10	1111	Sample 1
chr10	11111	Sample 1
chr10	111111	Sample 1
chr1	1	Sample 2
chr1	11	Sample 2
chr1	111	Sample 2
chr1	1111	Sample 2
chr1	11111	Sample 2
chr1	111111	Sample 2
chr2	1	Sample 2
chr2	22	Sample 2
chr2	111	Sample 2
chr2	2222	Sample 2
chr2	11111	Sample 2
chr2	111111	Sample 2
chr10	1	Sample 2
chr10	11	Sample 2
chr10	111	Sample 2
chr10	1111	Sample 2
chr10	11111	Sample 2
chr10	111111	Sample 2
chr1	1	Sample 10
chr1	11	Sample 10
chr1	111	Sample 10
chr1	1111	Sample 10
chr1	11111	Sample 10
chr1	111111	Sample 10
chr2	1	Sample 10
chr2	22	Sample 10
chr2	111	Sample 10
chr2	2222	Sample 10
chr2	11111	Sample 10
chr2	111111	Sample 10
chr10	1	Sample 10
chr10	11	Sample 10
chr10	111	Sample 10
chr10	1111	Sample 10
chr10	11111	Sample 10
chr10	111111	Sample 10
EOF
    export tmp
}

parsort_test() {
    echo "### parsort $@"
    parsort "$@"   "$tmp" | md5sum
    sort    "$@"   "$tmp" | md5sum
    parsort "$@" < "$tmp" | md5sum
    sort    "$@" < "$tmp" | md5sum
}
export -f parsort_test

par_normal() { parsort_test; }

par_n() { parsort_test -n; }

par_r() { parsort_test -r; }

par_nr() { parsort_test -nr; }

par_z() { parsort_test -z; }

par_k2() { parsort_test -k2n; }

par_k2r() { parsort_test -k2nr; }

par_k3() { parsort_test -k3; }

par_k3r() { parsort_test -k3r; }

par_dummy() {
    parsort_test --random-source=`which parallel` --batch-size=10 \
      --compress-program=gzip --temporary-directory=/var/tmp \
      --parallel=8 --unique
    # TODO
    #   files0=$(tempfile)
    #   echo $tmp > $files0
    #   --files0-from=$files0
}

par_tmpdir() {
    export TMPDIR="/tmp/parsort  dir"
    rm -rf "$TMPDIR"
    echo Should fail
    echo Fail: no such dir | parsort
    mkdir "$TMPDIR"
    echo OK | parsort
    chmod -w "$TMPDIR"
    echo Should fail
    echo Fail: writeable | parsort
    rm -rf "$TMPDIR"
}

setup

export -f $(compgen -A function | grep par_)
compgen -A function | grep par_ | LC_ALL=C sort |
    parallel --timeout 10000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'
