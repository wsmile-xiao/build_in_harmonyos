#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_space() {
    echo '### Test --env  - https://savannah.gnu.org/bugs/?37351'
    export TWOSPACES='  2  spaces  '
    export THREESPACES=" >  My brother's 12\" records  < "
    echo a"$TWOSPACES"b 1
    stdout parallel --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1
    stdout parallel -S localhost --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1
    stdout parallel -S csh@localhost --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1
    stdout parallel -S tcsh@localhost --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1

    echo a"$TWOSPACES"b a"$THREESPACES"b 2
    stdout parallel --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2
    stdout parallel -S localhost --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2
    stdout parallel -S csh@localhost --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2
    stdout parallel -S tcsh@localhost --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2

    echo a"$TWOSPACES"b a"$THREESPACES"b 3
    stdout parallel --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
    stdout parallel -S localhost --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
    stdout parallel -S csh@localhost --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
    stdout parallel -S tcsh@localhost --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
}

par_space_quote() {
    export MIN="  \'\""
    echo a"$MIN"b 4
    stdout parallel --env MIN echo 'a"$MIN"b' ::: 4
    stdout parallel -S localhost --env MIN echo 'a"$MIN"b' ::: 4
    stdout parallel -S csh@localhost --env MIN echo 'a"$MIN"b' ::: 4
    stdout parallel -S tcsh@localhost --env MIN echo 'a"$MIN"b' ::: 4
}

par_special_char() {
    export SPC="'"'   * ? >o  <i*? ][\!#¤%=( ) | }'
    echo a"$SPC"b 5
    LANG=C stdout parallel --env SPC echo 'a"$SPC"b' ::: 5
    LANG=C stdout parallel -S localhost --env SPC echo 'a"$SPC"b' ::: 5
    # \ misses due to quoting incompatiblilty between bash and csh
    LANG=C stdout parallel -S csh@localhost --env SPC echo 'a"$SPC"b' ::: 5
    LANG=C stdout parallel -S tcsh@localhost --env SPC echo 'a"$SPC"b' ::: 5
}

test_chr_on_sshlogin() {
    # test_chr_on_sshlogin 10,92 2/:,2/lo
    # test_chr_on_sshlogin 10,92 2/tcsh@lo,2/csh@lo
    chr="$1"
    sshlogin="$2"
    onall="$3"
    perl -e 'for('$chr') { printf "%c%c %c%d\0",$_,$_,$_,$_ }' |
	stdout parallel -j4 -k -I // --arg-sep _ -0 V=// V2=V2=// LANG=C parallel -k -j1 $onall -S $sshlogin --env V,V2,LANG echo \''"{}$V$V2"'\' ::: {#} {#} {#} {#} |
	sort |
	uniq -c |
	grep -av '   4 '|
	grep -av xauth |
	grep -av X11
}
export -f test_chr_on_sshlogin

par_env_newline_backslash_bash() {
    echo '### Test --env for \n and \\ - single and double (bash only) - no output is good'
    test_chr_on_sshlogin 10,92 2/:,2/lo ''
}

par_env_newline_backslash_csh() {
    echo '### Test --env for \n and \\ - single and double (*csh only) - no output is good but csh fails'
    test_chr_on_sshlogin 10,92  2/csh@lo '' | perl -pe "s/'(.)'/\$1/g"
    test_chr_on_sshlogin 10,92 2/tcsh@lo '' | perl -pe "s/'(.)'/\$1/g"
}

par_env_newline_backslash_onall_bash() {
    echo '### Test --env for \n and \\ - single and double --onall (bash only) - no output is good'
    test_chr_on_sshlogin 10,92 :,lo --onall |
	grep -v "Unmatched '\"'"
}

par_env_newline_backslash_onall_csh() {
    echo '### Test --env for \n and \\ - single and double --onall (*csh only) - no output is good but csh fails'
    test_chr_on_sshlogin 10,92 2/tcsh@lo,2/csh@lo --onall
}

par_env_160() {
    echo '### Test --env for \160 - which kills csh - single and double - no output is good'
    test_chr_on_sshlogin 160 :,1/lo,1/tcsh@lo |
	grep -v '   3 '
}

par_env_160_onall() {
    echo '### Test --env for \160  - which kills csh - single and double --onall - no output is good'
    test_chr_on_sshlogin 160 :,1/lo,1/tcsh@lo --onall |
	grep -a -v '   3 '
}

par_PARALLEL_RSYNC_OPTS() {
    echo '### test rsync opts'
    touch parallel_rsync_opts.test

    parallel --rsync-opts -rlDzRRRR -vv -S parallel@lo --trc {}.out touch {}.out ::: parallel_rsync_opts.test |
	perl -nE 's/(\S+RRRR)/say $1/ge'
    export PARALLEL_RSYNC_OPTS=-zzzzrldRRRR
    parallel -vv -S parallel@lo --trc {}.out touch {}.out ::: parallel_rsync_opts.test |
	perl -nE 's/(\S+RRRR)/say $1/ge'
    rm parallel_rsync_opts.test parallel_rsync_opts.test.out
    echo
}

par_controlmaster_is_faster() {
    echo '### bug #41964: --controlmaster not seems to reuse OpenSSH connections to the same host'
    echo '-M should finish first - eventhough there are 2x jobs'
    export SSHLOGIN1=sh@lo
    nl="$(printf "\n\n.")"
    export TMPDIR="/tmp/ctrl_master/$nl'$nl"
    mkdir -p "$TMPDIR"
    (parallel -S $SSHLOGIN1 true ::: {1..20};
     echo No --controlmaster - finish last) &
    (parallel -M -S $SSHLOGIN1 true ::: {1..40};
     echo With --controlmaster - finish first) &
    wait
    rm -r "/tmp/ctrl_master"
}

par_hostgroup() {
    echo '### --hostgroup force ncpu - 2x parallel, 6x me'
    parallel --delay 0.1 --hgrp -S @g1/1/parallel@lo -S @g2/3/lo \
	     'whoami;sleep 0.4{}' ::: {1..8} | sort

    echo '### --hostgroup two group arg - 2x parallel, 6x me'
    parallel -k --sshdelay 0.1 --hgrp -S @g1/1/parallel@lo -S @g2/3/lo \
	     'whoami;sleep 0.3{}' ::: {1..8}@g1+g2 | sort

    echo '### --hostgroup one group arg - 8x me'
    parallel --delay 0.2 --hgrp -S @g1/1/parallel@lo -S @g2/3/lo \
	     'whoami;sleep 0.4{}' ::: {1..8}@g2

    echo '### --hostgroup multiple group arg + unused group - 2x parallel, 6x me, 0x tcsh'
    parallel --delay 0.2 --hgrp -S @g1/1/parallel@lo -S @g1/3/lo -S @g3/30/tcsh@lo \
	     'whoami;sleep 0.8{}' ::: {1..8}@g1+g2 2>&1 | sort -u | grep -v Warning

    echo '### --hostgroup two groups @'
    parallel -k --hgrp -S @g1/parallel@lo -S @g2/lo --tag whoami\;echo ::: parallel@g1 tange@g2

    echo '### --hostgroup'
    parallel -k --hostgroup -S @grp1/lo echo ::: no_group explicit_group@grp1 implicit_group@lo

    echo '### --hostgroup --sshlogin with @'
    parallel -k --hostgroups -S parallel@lo echo ::: no_group implicit_group@parallel@lo

    echo '### --hostgroup -S @group - bad if you get parallel@lo'
    parallel -S @g1/ -S @g1/1/tcsh@lo -S @g1/1/localhost -S @g2/1/parallel@lo \
	     'whoami;true' ::: {1..6} | sort -u

    echo '### --hostgroup -S @group1 -Sgrp2 - get all twice'
    parallel -S @g1/ -S @g2/ -S @g1/1/tcsh@lo -S @g1/1/localhost -S @g2/1/parallel@lo \
	     'whoami;sleep 1;true' ::: {1..6} | sort

    echo '### --hostgroup -S @group1+grp2 - get all twice'
    parallel -S @g1+g2/ -S @g1/1/tcsh@lo -S @g1/1/localhost -S @g2/1/parallel@lo \
	     'whoami;sleep 1;true' ::: {1..6} | sort
}

par_retries_bug_from_2010() {
    echo '### Bug with --retries'
    seq 1 8 |
	parallel --retries 2 --sshlogin 8/localhost,8/: -j+0 "hostname; false" |
	wc -l
    seq 1 8 |
	parallel --retries 2 --sshlogin 8/localhost,8/: -j+1 "hostname; false" |
	wc -l
    seq 1 2 |
	parallel --retries 2 --sshlogin 8/localhost,8/: -j-1 "hostname; false" |
	wc -l
    seq 1 1 |
	parallel --retries 2 --sshlogin 1/localhost,1/: -j1 "hostname; false" |
	wc -l
    seq 1 1 |
	parallel --retries 2 --sshlogin 1/localhost,1/: -j9 "hostname; false" |
	wc -l
    seq 1 1 |
	parallel --retries 2 --sshlogin 1/localhost,1/: -j0 "hostname; false" |
	wc -l

    echo '### These were not affected by the bug'
    seq 1 8 |
	parallel --retries 2 --sshlogin 1/localhost,9/: -j-1 "hostname; false" |
	wc -l
    seq 1 8 |
	parallel --retries 2 --sshlogin 8/localhost,8/: -j-1 "hostname; false" |
	wc -l
    seq 1 1 |
	parallel --retries 2 --sshlogin 1/localhost,1/:  "hostname; false" |
	wc -l
    seq 1 4 |
	parallel --retries 2 --sshlogin 2/localhost,2/: -j-1 "hostname; false" |
	wc -l
    seq 1 4 |
	parallel --retries 2 --sshlogin 2/localhost,2/: -j1 "hostname; false" |
	wc -l
    seq 1 4 |
	parallel --retries 2 --sshlogin 1/localhost,1/: -j1 "hostname; false" |
	wc -l
    seq 1 2 |
	parallel --retries 2 --sshlogin 1/localhost,1/: -j1 "hostname; false" |
	wc -l
}

export -f $(compgen -A function | grep par_)
#compgen -A function | grep par_ | sort | parallel --delay $D -j$P --tag -k '{} 2>&1'
compgen -A function | grep par_ | sort |
    parallel --joblog /tmp/jl-`basename $0` --retries 3 -j2 --tag -k '{} 2>&1'
