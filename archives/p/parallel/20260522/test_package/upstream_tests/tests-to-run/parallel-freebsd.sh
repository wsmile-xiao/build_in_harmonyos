#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo "### These tests requires VirtualBox running with the following images"
SERVER1=freebsd14
SSHUSER1=vagrant
SSHLOGIN1=$SSHUSER1@$SERVER1
echo $SSHUSER1@$SERVER1

ssh $SSHLOGIN1 touch .parallel/will-cite
(
    pwd=$(pwd)
    # If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
    testsuitedir=${testsuitedir:-$pwd}
    cd $testsuitedir 
    scp -q "$testsuitedir"/../src/{parallel,sem,sql,niceload,env_parallel*} $SSHLOGIN1:bin/
)
# Moving the functions to FreeBSD is a bit tricky:
#   We use env_parallel.bash to copy the functions to FreeBSD
. env_parallel.bash
env_parallel --session

par_no_more_procs() {
    echo 'bug #40136: FreeBSD: No more processes'
    sem --jobs 3 --id my_id -u 'echo First started; sleep 10; echo The first finished;echo' &&
	sem --jobs 3 --id my_id -u 'echo Second started; sleep 11; echo The second finished;echo' &&
	sem --jobs 3 --id my_id -u 'echo Third started; sleep 12; echo The third finished;echo' &&
	sem --jobs 3 --id my_id -u 'echo Fourth started; sleep 13; echo The fourth finished;echo' &&
	sem --wait --id my_id
}

par_compress_pipe() {
    echo 'Test --compress --pipe'
    jot 1000 | parallel --compress --pipe cat | wc

    echo 'bug #41613: --compress --line-buffer no newline'
    perl -e 'print "It worked"'| parallel --pipe --compress --line-buffer cat
    echo
}

par_sem_fg() {
    echo 'bug #40135: FreeBSD: sem --fg does not finish under /bin/sh'
    sem --fg 'sleep 1; echo The job finished'
}

par_round_robin() {
    echo 'bug #40133: FreeBSD: --round-robin gives no output'
    jot 1000000 | parallel --round-robin --pipe -kj3 cat | wc
    jot 1000000 | parallel --round-robin --pipe -kj4 cat | wc
}

par_shebang() {
    echo 'bug #40134: FreeBSD: --shebang not working'
    (echo '#!/usr/bin/env -S parallel --shebang -rk echo'
     echo It
     echo worked) > shebang
    chmod 755 ./shebang; ./shebang

    echo 'bug #40134: FreeBSD: --shebang(-wrap) not working'
    (echo '#!/usr/bin/env -S parallel --shebang-wrap /usr/local/bin/perl :::';
     echo 'print @ARGV,"\n";') > shebang-wrap
    chmod 755 ./shebang-wrap
    ./shebang-wrap wrap works | sort -r

    echo 'bug #40134: FreeBSD: --shebang(-wrap) with options not working'
    (echo '#!/usr/bin/env -S parallel --shebang-wrap -v -k -j 0 /usr/local/bin/perl -w :::'
     echo 'print @ARGV,"\n";') > shebang-wrap-opt;
    chmod 755 ./shebang-wrap-opt
    ./shebang-wrap-opt wrap works with options
}

par_load() {
    echo '### Test --load (must give 1=true)'
    parallel -j0 -N0 --timeout 5 --nice 10 'bzip2 < /dev/zero >/dev/null' ::: 1 2 3 4 5 6 &
    parallel --argsep ,, --joblog - -N0 parallel --load 100% echo ::: 1 ,, 1 |
	# Must take > 5 sec
	parallel -k --colsep '\t' --header :  echo '{=4 $_=$_>5=}'
}

par_env_parallel() {
    echo "### env_parallel on Freebsd"
    . bin/env_parallel.sh
    myvar="`echo 'myvar_line  1'; echo 'myvar_line  2'`"
    alias myalias='echo myalias1 "$myvar";'"`echo` echo myalias2"
    env_parallel myalias ::: foo
}

#   GNU/Linux runs bash, but the FreeBSD runs (a)sh,
#   (a)sh does not support 'export -f' so any function exported
#   must be unset

unset replace_tmpdir
unset run_once
unset run_test
unset TMPDIR

#   As the copied environment is written in Bash dialect
#   we get 'shopt'-errors and 'declare'-errors.
#   We can safely ignore those.
export LC_ALL=C
PARALLEL_SHELL=sh env_parallel --timeout 100 -vj4 -k --joblog /tmp/jl-`basename $0` --retries 3 \
	     -S $SSHLOGIN1 --tag '{} 2>&1' \
	     ::: $(compgen -A function | G "$@" par_ | sort) \
	     2> >(grep -Ev 'shopt: not found|declare: not found')
