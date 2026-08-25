#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_memory_leak() {
    a_run() {
	seq $1 |time -v parallel true 2>&1 |
	grep 'Maximum resident' |
	field 6;
    }
    export -f a_run
    echo "### Test for memory leaks"
    echo "Of 300 runs of 1 job at least one should be bigger than a 3000 job run"
    . env_parallel.bash
    parset small_max,big_min {} ::: \
	   'seq 300 | parallel a_run 1    | jq -s max' \
	   'seq 3   | parallel a_run 3000 | jq -s min'
    echo "`date` [ $small_max < $big_min ]" >> /tmp/parallel-mem-leak.out
    if [ $(($small_max)) -lt $big_min ] ; then
	echo "Bad: Memleak likely. [ $small_max < $big_min ]"
    else
	echo "Good: No memleak detected."
    fi
}
export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | sort |
    parallel --delay 0.3 --timeout 300% -j6 --lb --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'
