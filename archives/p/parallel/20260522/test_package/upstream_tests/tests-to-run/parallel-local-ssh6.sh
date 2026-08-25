#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# At most 2 parallel sshs per function

export SSHLOGIN1=parallel@lo
export SSHLOGIN2=csh@lo
mkdir -p tmp

par_termseq_remote() {
    echo '### bug #59146: Support --termseq for remote jobs'
    doit() {
	# setup signal handlers for all signals
	exec perl -e '
	$file = shift;
    for $i (qw(
    HUP      INT      QUIT     ILL      TRAP
    ABRT     BUS      FPE      KILL     USR1
    SEGV     USR2     PIPE     ALRM     TERM
    STKFLT   CHLD     CONT     STOP     TSTP
    TTIN     TTOU     URG      XCPU     XFSZ
    VTALRM   PROF     WINCH    IO       PWR
    SYS      RTMIN    RTMIN+1  RTMIN+2  RTMIN+3
    RTMIN+4  RTMIN+5  RTMIN+6  RTMIN+7  RTMIN+8
    RTMIN+9  RTMIN+10 RTMIN+11 RTMIN+12 RTMIN+13
    RTMIN+14 RTMIN+15 RTMAX-14 RTMAX-13 RTMAX-12
    RTMAX-11 RTMAX-10 RTMAX-9  RTMAX-8  RTMAX-7
    RTMAX-6  RTMAX-5  RTMAX-4  RTMAX-3  RTMAX-2
    RTMAX-1  RTMAX
	    )) {
	    eval q[$SIG{].$i.q[}=sub{open(A,">>$file");print A "].$i.q[\n";};];
	}
	for(1..100) { sleep(1);}
	' $file
    }
    file=/tmp/sig$$
    . env_parallel.bash
    env_parallel -v --timeout 5 --termseq HUP,40,INT,40,QUIT,40,ILL,40,TRAP,40,ABRT,40,BUS,40,FPE,40,USR1,40,SEGV,40,USR2,40,PIPE,40,ALRM,40,TERM,40,STKFLT,40,CHLD,40,CONT,40,TSTP,40,TTIN,40,TTOU,40,URG,40,XCPU,40,XFSZ,40,VTALRM,40,PROF,40,WINCH,40,IO,40,PWR,40,SYS,40,RTMIN,40,RTMAX,40,KILL,9 -S $SSHLOGIN1 doit ::: 1
    sleep 5
    ssh $SSHLOGIN1 "sort $file; rm $file"
}

par_nonall_ssh() {
    echo 'bug #59181: --ssh is not propagated to --nonall'
    myssh() {
	echo >&2 "myssh called with args: $@"
	shift
	ssh "$@"
    }
    export -f myssh
    stdout parallel --ssh "myssh myarg" -S $SSHLOGIN1 --nonall echo run on all
}

par_test_onall() {
    echo '### Test --onall'
    parallel --onall --tag -k -S $SSHLOGIN1,$SSHLOGIN2 '(echo {1} {2}) | awk \{print\ \$2}' ::: a b c ::: 1 2
}

par_test_pipe_onall() {
    echo '### Test | --onall'
    seq 3 |
	parallel --onall --tag -k -S $SSHLOGIN1,$SSHLOGIN2 '(echo {1} {2}) | awk \{print\ \$2}' ::: a b c :::: -
}

par_test_onall_u() {
    echo '### Test --onall -u'
    parallel --onall -S $SSHLOGIN1,$SSHLOGIN2 -u '(echo {1} {2}) | awk \{print\ \$2}' ::: a b c ::: 1 2 3 |
	sort
}    

par_test_nonall() {
    echo '### Test --nonall'
    parallel --nonall -k -S $SSHLOGIN1,$SSHLOGIN2 pwd |
	perl -pe 's:/mnt/4tb::g' |
	sort
}    

par_test_nonall_u() {
    echo '### Test --nonall -u - should be interleaved x y x y'
    parallel --nonall -S $SSHLOGIN1,$SSHLOGIN2 -u 'pwd|grep -q csh && sleep 3; pwd;sleep 12;pwd;' |
	perl -pe 's:/mnt/4tb::g'
}    

par_read_sshloginfile_from_stdin() {
    echo '### Test read sshloginfile from STDIN'
    echo $SSHLOGIN1,$SSHLOGIN2 |
	parallel -S - -k --nonall pwd |
	perl -pe 's:/mnt/4tb::g'
    echo $SSHLOGIN1,$SSHLOGIN2 |
	parallel --sshloginfile - -k --onall pwd\; echo ::: foo |
	perl -pe 's:/mnt/4tb::g'
}

par_nonall_basefile() {
    echo '### Test --nonall --basefile'
    touch tmp/nonall--basefile
    stdout parallel --nonall --basefile tmp/nonall--basefile -S $SSHLOGIN1,$SSHLOGIN2 ls tmp/nonall--basefile
    stdout parallel --nonall -S $SSHLOGIN1,$SSHLOGIN2 rm tmp/nonall--basefile
    stdout rm tmp/nonall--basefile
}

par_onall_basefile() {
    echo '### Test --onall --basefile'
    touch tmp/onall--basefile
    stdout parallel --onall --basefile tmp/onall--basefile -S $SSHLOGIN1,$SSHLOGIN2 ls {} ::: tmp/onall--basefile
    stdout parallel --onall -S $SSHLOGIN1,$SSHLOGIN2 rm {} ::: tmp/onall--basefile
    stdout rm tmp/onall--basefile
}    

par_nonall_basefile_cleanup() {
    echo '### Test --nonall --basefile --cleanup (rm should fail)'
    touch tmp/nonall--basefile--clean
    stdout parallel --nonall --basefile tmp/nonall--basefile--clean --cleanup -S $SSHLOGIN1,$SSHLOGIN2 ls tmp/nonall--basefile--clean
    stdout parallel --nonall -S $SSHLOGIN1,$SSHLOGIN2 rm tmp/nonall--basefile--clean
    stdout rm tmp/nonall--basefile--clean
}

par_onall_basefile_cleanup() {
    echo '### Test --onall --basefile --cleanup (rm should fail)'
    touch tmp/onall--basefile--clean
    stdout parallel --onall --basefile tmp/onall--basefile--clean --cleanup -S $SSHLOGIN1,$SSHLOGIN2 ls {} ::: tmp/onall--basefile--clean
    stdout parallel --onall -S $SSHLOGIN1,$SSHLOGIN2 rm {} ::: tmp/onall--basefile--clean
    stdout rm tmp/onall--basefile--clean
}

par_workdir_dot() {
    echo '### Test --workdir .'
    ssh $SSHLOGIN1 mkdir -p mydir
    mkdir -p $HOME/mydir
    cd $HOME/mydir
    parallel --workdir . -S $SSHLOGIN1 ::: pwd |
	perl -pe 's:/mnt/4tb::g'
}

par_wd_dot() {
    echo '### Test --wd .'
    ssh $SSHLOGIN2 mkdir -p mydir
    mkdir -p $HOME/mydir
    cd $HOME/mydir
    parallel --workdir . -S $SSHLOGIN2 ::: pwd |
	perl -pe 's:/mnt/4tb::g'
}    

par_wd_braces() {
    echo '### Test --wd {}'
    ssh $SSHLOGIN2 rm -rf wd1 wd2
    mkdir -p $HOME/mydir
    cd $HOME/mydir
    parallel --workdir {} -S $SSHLOGIN2 touch ::: wd1 wd2
    ssh $SSHLOGIN2 ls -d wd1 wd2
}

par_wd_perlexpr() {
    echo '### Test --wd {= =}'
    ssh $SSHLOGIN2 rm -rf WD1 WD2
    mkdir -p $HOME/mydir
    cd $HOME/mydir
    parallel --workdir '{= $_=uc($_) =}' -S $SSHLOGIN2 touch ::: wd1 wd2
    ssh $SSHLOGIN2 ls -d WD1 WD2
}

par_nonall_wd() {
    echo '### Test --nonall --wd'
    parallel --workdir /tmp -S $SSHLOGIN2 --nonall pwd
}

par_remote_symlink_dir() {
    echo 'bug #51293: parallel does not preserve symlinked directory structure on remote'
    ssh parallel@lo 'mkdir -p tmp; rm -rf wd; ln -s tmp wd'
    mkdir -p wd
    touch wd/testfile
    parallel --nonall --rsync-opts '--keep-dirlinks -rlDzR' -S parallel@lo --basefile wd/testfile
    ssh parallel@lo rm wd && echo OK: wd is still a symlink with --rsync-opts

    ssh parallel@lo 'mkdir -p tmp; rm -rf wd; ln -s tmp wd'
    mkdir -p wd
    touch wd/testfile
    export PARALLEL_RSYNC_OPTS='--keep-dirlinks -rlDzR'
    parallel --nonall -S parallel@lo --basefile wd/testfile
    ssh parallel@lo rm wd && echo OK: wd is still a symlink with PARALLEL_RSYNC_OPTS
}

par_sshlogin_replacement() {
    echo '### show {sshlogin} and {host}'
    parallel -S $SSHLOGIN1 --plus echo {sshlogin} {} {host} ::: and
    parallel -S '5//usr/bin/ssh '$SSHLOGIN1 --plus echo {sshlogin} {} {host} ::: and
}

par_onall_timeout() {
    echo '### --timeout --onall on remote machines: 2*slept 1, 2 jobs failed'
    parallel -j0 --timeout 6 --onall -S localhost,$SSHLOGIN1 'sleep {}; echo slept {}' ::: 1 8 9
    echo jobs failed: $?
}

par_rsync_3.2.3() {
    echo "bug #59006: rsync version 3.2.3 is not detected correctly"
    tmp=$(mktemp -d)
    cp $(which rsync-v3.2.3) "$tmp"/rsync
    PATH="$tmp":$PATH
    rsync --version | grep version
    rm -f bug59006
    parallel --return {} -Sparallel@lo touch ::: bug59006
    ls bug59006
    rm -f bug59006
    rm -r "$tmp"
}

export -f $(compgen -A function | grep par_)
#compgen -A function | grep par_ | sort | parallel --delay $D -j$P --tag -k '{} 2>&1'
compgen -A function | G par_ "$@" | sort |
    parallel --joblog /tmp/jl-`basename $0` -j5 --tag -k '{} 2>&1'
