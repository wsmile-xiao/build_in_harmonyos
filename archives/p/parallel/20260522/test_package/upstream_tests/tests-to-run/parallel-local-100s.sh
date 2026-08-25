#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Simple jobs that never fails
# Each should be taking 100-300s and be possible to run in parallel
# I.e.: No race conditions, no logins

# tmpdir with > 5 GB available
TMP5G=${TMP5G:-/dev/shm}
export TMP5G

rm -f /tmp/*.{tmx,pac,arg,all,log,swp,loa,ssh,df,pip,tmb,chr,tms,par}

par_--shellquote_command_len() {
    echo '### test quoting will not cause a crash if too long'
    # echo "'''" | parallel --shellquote --shellquote --shellquote --shellquote
    export PARALLEL="--unsafe"
    testlen() {
	echo "$1" | parallel $2 | wc
    }
    export -f testlen

    outer() {
	export PARALLEL="$PARALLEL --env testlen -k --tag"
	parallel $@ testlen '{=2 $_="$arg[1]"x$_ =}' '{=3 $_=" --shellquote"x$_ =}' \
	     ::: '"' "'" ::: {1..10} ::: {1..10}
    }
    export -f outer

    stdout parallel --tag -k outer ::: '-Slo -j10' '' |
	perl -pe 's/(\d+)\d\d\d\d/${1}xxxx/g';
}

par_squared() {
    export PARALLEL="--load 300% --unsafe"
    squared() {
	i=$1
	i2=$[i*i]
	seq $i2 | parallel -j0 --load 300% -kX echo {} | wc
	seq 1 ${i2}0000 |
	    parallel -kj20 --recend "\n" --spreadstdin gzip -1 |
	    zcat | sort -n | md5sum
    }
    export -f squared

    seq 10 -1 2 | stdout parallel -j5 -k squared |
	grep -Ev 'processes took|Consider adjusting -j'
}

linebuffer_matters() {
    echo "### (--linebuffer) --compress $TAG should give different output"
    nolbfile=$(mktemp)
    lbfile=$(mktemp)
    controlfile=$(mktemp)
    randomfile=$(mktemp)
    # Random data because it does not compress well
    # forcing the compress tool to spit out compressed blocks
    perl -pe 'y/[A-Za-z]//cd; $t++ % 1000 or print "\n"' < /dev/urandom |
	head -c 10000000 > "$randomfile"
    export randomfile

    testfunc() {
	linebuffer="$1"

	incompressible_ascii() {
	    # generate some incompressible ascii
	    # with lines starting with the same string
	    id=$1
	    shuf "$randomfile" | perl -pe 's/^/'$id' /'
	    # Sleep to give time to linebuffer-print the first part
	    sleep 10
	    shuf "$randomfile" | perl -pe 's/^/'$id' /'
	    echo
	}
	export -f incompressible_ascii

	nowarn() {
	    # Ignore certain warnings
	    # parallel: Warning: Starting 11 processes took > 2 sec.
	    # parallel: Warning: Consider adjusting -j. Press CTRL-C to stop.
	    grep -v '^parallel: Warning: (Starting|Consider)' >&2
	}

	parallel -j0 $linebuffer --compress $TAG \
		 incompressible_ascii ::: {0..10} 2> >(nowarn) |
	    perl -ne '/^(\d+)\s/ and print "$1\n"' |
	    uniq |
	    sort
    }

    # These can run in parallel if there are enough ressources
    testfunc > "$nolbfile"
    testfunc > "$controlfile"
    testfunc --linebuffer > "$lbfile"
    wait

    nolb="$(cat "$nolbfile")"
    control="$(cat "$controlfile")"
    lb="$(cat "$lbfile")"
    rm "$nolbfile" "$lbfile" "$controlfile" "$randomfile"

    if [ "$nolb" == "$control" ] ; then
	if [ "$lb" == "$nolb" ] ; then
	    echo "BAD: --linebuffer makes no difference"
	else
	    echo "OK: --linebuffer makes a difference"
	fi
    else
	echo "BAD: control and nolb are not the same"
    fi
}
export -f linebuffer_matters

par_linebuffer_matters_compress_tag() {
    export TAG=--tag
    linebuffer_matters
}

par_linebuffer_matters_compress() {
    linebuffer_matters
}

par_linebuffer_files() {
    echo 'bug #48658: --linebuffer --files'
    rm -rf /tmp/par48658-*

    doit() {
	compress="$1"
	echo "normal"
	parallel --linebuffer --compress-program $compress seq ::: 100000 |
	    wc -l
	echo "--files"
	parallel --files --linebuffer --compress-program $1 seq ::: 100000 |
	    wc -l
	echo "--results"
	parallel --results /tmp/par48658-$compress --linebuffer --compress-program $compress seq ::: 100000 |
	    wc -l
	rm -rf "/tmp/par48658-$compress"
    }
    export -f doit
    # lrz complains 'Warning, unable to set nice value on thread'
    parallel -j1 --tag -k doit ::: zstd pzstd clzip lz4 lzop pigz pixz gzip plzip pbzip2 lzma xz lzip bzip2 lbzip2 lrz
}

par_timeout() {
    echo "### test --timeout"
    stdout time -f %e parallel --timeout 1s sleep ::: 10 |
	perl -ne '1 < $_ and $_ < 10 and print "OK\n"'
    stdout time -f %e parallel --timeout 1m sleep ::: 100 |
	perl -ne '10 < $_ and $_ < 100 and print "OK\n"'
}

par_bug57364() {
    echo '### bug #57364: Race condition creating len cache file.'
    j=32
    set -e
    for i in $(seq 1 50); do
        # Clear cache (simple 'rm -rf' causes race condition)
        mv "${HOME}/.parallel/tmp" "${HOME}/.parallel/tmp-$$" &&
            rm -rf "${HOME}/.parallel/tmp-$$"
        # Try to launch multiple parallel simultaneously.
        seq $j |
            xargs -P $j -n 1 parallel true $i :::
    done 2>&1
}

#par_crashing() {
#    echo '### bug #56322: sem crashed when running with input from seq'
#    echo "### This should not fail"
#    doit() { seq 100000000 |xargs -P 80 -n 1 sem true; }
#    export -f doit
#    parallel -j1 --timeout 100 --nice 11 doit ::: 1
#}

par_z_roundrobin_blocks() {
    echo "bug #49664: --round-robin does not complete"
    seq 20000000 | parallel -j8 --block 10M --round-robin --pipe wc -c | wc -l
}

par_groupby_compressed() {
    echo '### --groupby --pipepart on plain and gzip files give same line counts'
    seq 1 20 | awk '{print (NR%3), $1}' | sort -k1 > /tmp/test_groupby_plain.txt
    gzip -c /tmp/test_groupby_plain.txt > /tmp/test_groupby_plain.gz
    parallel --pipepart -a /tmp/test_groupby_plain.txt --groupby 1 -k 'wc -l' | sort
    parallel --pipepart -a /tmp/test_groupby_plain.gz  --groupby 1 -k 'wc -l' | sort
    rm /tmp/test_groupby_plain.txt /tmp/test_groupby_plain.gz
}

export -f $(compgen -A function | grep par_)
compgen -A function | grep par_ | LC_ALL=C sort |
    parallel --timeout 1000% -j10 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'
