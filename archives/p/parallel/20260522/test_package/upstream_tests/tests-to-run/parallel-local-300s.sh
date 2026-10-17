#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Simple jobs that never fails
# Each should be taking >300s and be possible to run in parallel
# I.e.: No race conditions, no logins

# tmpdir with > 5 GB available
TMP5G=${TMP5G:-/dev/shm}
export TMP5G

rm -f /tmp/*.{tmx,pac,arg,all,log,swp,loa,ssh,df,pip,tmb,chr,tms,par}

par_compare_exit_codes() {
    echo '### compare the exit codes'
    echo 'directly from shells, shells called from parallel,'
    echo 'killed with different signals'
    # run:
    # *  exit $val
    # *  kill -$1 $$'
    # both:
    # *  under different shells
    # *  from parallel running under different shells
    # record:
    # *  exit value
    # *  signal
    echo sig=joblog_sig shell=parallel=joblog
    # The quoting of \n is wrong for csh, so just use a sane TMPDIR here
    TMPDIR=/tmp/par-300s
    export TMPDIR
    mkdir -p "$TMPDIR"
    
    selfkill=$(mktemp)
    qselfkill=$(parallel -0 --shellquote ::: "$selfkill")
    qqselfkill=$(parallel -0 --shellquote --shellquote ::: "$selfkill")
    export selfkill qselfkill qqselfkill
    echo 'kill -$1 $$' >"$selfkill"
    exit=$(mktemp)
    qexit=$(parallel -0 --shellquote ::: "$exit")
    qqexit=$(parallel -0 --shellquote --shellquote ::: "$exit")
    export exit qexit qqexit
    echo 'exit $1' >"$exit"

    doit() {
	shell=$1
	sig=$2
	sig128=$(( sig + 128 ))
	sh -c "$shell $qselfkill $sig" 2>/dev/null
	raw=$?
	sh -c "$shell $qexit $sig128" 2>/dev/null
	raw128=$?
	
	log=$(mktemp)
	qlog=$(parallel -0 --shellquote ::: "$log")
	qqlog=$(parallel -0 --shellquote --shellquote ::: "$log")
	$shell -c "parallel --halt now,done=1 --jl $qlog $shell $qqselfkill ::: $sig" 2>/dev/null
	#echo parallel $shell $sig = $?
	parallel=$?
	joblog_exit=$(field 7 < "$log" | tail -n1)
	joblog_signal=$(field 8 < "$log" | tail -n1)
	$shell -c "parallel --halt now,done=1 --jl $qlog $shell $qqexit ::: $sig128" 2>/dev/null
	parallel128=$?
	joblog_exit128=$(field 7 < "$log" | tail -n1)
	joblog_signal128=$(field 8 < "$log" | tail -n1)

	rm "$log"
	
	echo $shell sig' ' $sig=$joblog_signal $raw=$parallel=$joblog_exit
	echo $shell exit $sig128=$joblog_signal128 $raw128=$parallel128=$joblog_exit128
    }
    export -f doit

    # These give the same exit code prepended with 'true;' or not
    OK="ash csh dash fish fizsh posh rc sash sh tcsh"
    # These do not give the same exit code prepended with 'true;' or not
    BAD="bash ksh93 mksh static-sh yash zsh"
    (
	# Most block on signals: 19+20+21+22
	ulimit -n `ulimit -Hn`
	parallel -j1000% -k doit ::: $OK $BAD ::: {1..18}  {23..64}
	# fdsh blocks on a lot more signals
	parallel -j1000% -k doit ::: fdsh ::: 2 {9..12} {14..18} {20..23} 26 27 29 30 {32..64}
   ) |
	# Ignore lines where the exit codes are the same
	perl -ne '/(\d+)=\1=\1/ or print'
    rm "$selfkill" "$exit"
    rmdir "$TMPDIR"
}

par_retries_unreachable() {
  echo '### Test of --retries on unreachable host'
  seq 2 | stdout parallel -k --retries 2 -v -S 4.3.2.1,: echo
}

par_outside_file_handle_limit() {
    ulimit -n 1024
    echo "### Test Force outside the file handle limit, 2009-02-17 Gave fork error"
    (echo echo Start; seq 1 20000 | perl -pe 's/^/true /'; echo echo end) |
	stdout parallel -uj 0 | egrep -v 'processes took|adjusting' |
	perl -pe 's/\d\d\d/999/'
}

par_over_4GB() {
    echo '### Test if we can deal with output > 4 GB'
    echo |
	nice parallel --tmpdir $TMP5G -q perl -e '$a="x"x1000000;for(0..4300){print $a}' |
	nice md5sum
}

par_xhalt_on_error() {
    mytest() {
	HALT=$1
	BOOL1=$2
	BOOL2=$3
	(echo "sleep 2;$BOOL1";
	    echo "sleep 3;$BOOL2";
	    echo "sleep 4;$BOOL1") |
	    parallel -j10 --halt-on-error $HALT
	echo $?
	(echo "sleep 2;$BOOL1";
	    echo "sleep 3;$BOOL2";
	    echo "sleep 4;$BOOL1";
	    echo "sleep 5;non_exist";
	) |
	    parallel -j10 --halt-on-error $HALT
	echo $?
    }
    export -f mytest
    parallel -j1 -k --tag mytest ::: -2 -1 0 1 2 ::: true false ::: true false
}

par__test_build_and_install() {
    cd ~/privat/parallel
    # Make a .tar.gz file
    stdout make dist |
	perl -pe 's/make\[\d\]/make[0]/g;s/\d{8}/00000000/g'
    LAST=$(ls *tar.gz | tail -n1)

    cd /tmp
    rm -rf parallel-20??????/
    tar xf ~/privat/parallel/$LAST
    cd parallel-20??????/
    rm -rf /tmp/parallel-install

    echo "### Test normal build and install"
    # Make sure files depending on *.pod have to be rebuilt
    touch src/*pod src/sql
    ./configure --prefix=/tmp/parallel-install &&
	(stdout nice make -j3 >/dev/null;
	 stdout nice make install) |
	    perl -pe 's/make\[\d\]/make[0]/g;
		      s/rm: cannot remove.*\n//;
		      s/\d{8}/00000000/g'

    echo '### Test installation missing pod2*'
    parallel which ::: pod2html pod2man pod2texi pod2pdf |
	sudo parallel mv {} {}.hidden
    # Make sure files depending on *.pod have to be rebuilt
    touch src/*pod src/sql
    ./configure --prefix=/tmp/parallel-install &&
	(stdout nice make -j3 >/dev/null;
	 stdout nice make install) |
	    perl -pe 's/make\[\d\]/make[0]/g;
		      s/rm: cannot remove.*\n//;
		      s/\d{8}/00000000/g'

    parallel which {}.hidden ::: pod2html pod2man pod2texi pod2pdf |
	sudo parallel mv {} {.}
}

#par_crashing() {
#    echo '### bug #56322: sem crashes when running with input from seq'
#    echo "### This should time out - not fail"
#    doit() { seq 100000000 |xargs -P 80 -n 1 sem true; }
#    export -f doit
#    stdout parallel -j1 --timeout 100 --nice 11 doit ::: 1
#}

export -f $(compgen -A function | grep par_)
compgen -A function | G "$@" par_ | LC_ALL=C sort |
    parallel --timeout 1000% -j10 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g'
