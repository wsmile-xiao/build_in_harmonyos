#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo Retired 2026-05-22
exit 0

# Check servers up on http://www.polarhome.com/service/status/
unset TIMEOUT
. env_parallel.bash
env_parallel --session

P_ALL="openstep qnx pidora alpha tru64 hpux-ia64 syllable raspbian solaris openindiana aix hpux debian-ppc suse solaris-x86 mandriva ubuntu scosysv unixware centos miros macosx redhat netbsd openbsd freebsd debian dragonfly vax ultrix minix irix hurd beaglebone cubieboard2"
# Skip ultrix
# Skip irix until Perl is upgraded (I cannot due to too small disk quota)
P_ALL="openstep qnx pidora alpha tru64 hpux-ia64 syllable raspbian solaris openindiana aix hpux debian-ppc suse solaris-x86 mandriva ubuntu scosysv unixware centos miros macosx redhat netbsd openbsd freebsd debian dragonfly vax minix hurd beaglebone cubieboard2"
P="$P_ALL"
#P="unixware freebsd netbsd"

# tru64 takes 22s to run 4 parallels
MAXTIME=50
RETRIES=3
# 11 too much for debian
MAXPROC=${maxproc:-9}
# 3 is too much for freebsd
MAXINNERPROC=${maxinnerproc:-2}

export PARALLEL_SSH="ssh -oLogLevel=quiet"

# select a running master (debian-ppc, suse, ubuntu, redhat, or debian)
# 2019-06-25 debian has too little free memory (and swap)
# 2020-04-22 debian-ppc has read-only disk
MASTER=$(parallel -j0 --delay 0.1 --halt now,success=1 $PARALLEL_SSH {} echo {} \
		  ::: {ubuntu,suse,redhat}.polarhome.com)

parallel -j0 --delay 0.1 --retries $RETRIES \
    rsync -L /usr/local/bin/{parallel,env_parallel,env_parallel.*[^~],parcat,stdout} \
    ::: $MASTER:bin/

doit() {
    # Avoid the stupid /etc/issue.net banner at Polarhome: -oLogLevel=quiet
    PARALLEL_SSH="ssh -oLogLevel=quiet"
    export PARALLEL_SSH
    export MAXTIME
    export RETRIES
    export MAXPROC
    export RET_TIME_K="--memfree 100m -k --retries $RETRIES --timeout $MAXTIME"
    LC_ALL=C
    . `which env_parallel.bash`
    env_parallel --session
    
    MAXPROC=$(echo $(seq 300 | parallel -j0 echo {%} | sort -n | tail -n1) /$MAXINNERPROC | bc)
    echo MAXTIME=$MAXTIME RETRIES=$RETRIES MAXPROC=$MAXPROC MAXINNERPROC=$MAXINNERPROC

    echo '### Filter out working servers'
    # pidora and syllable often gives false positive
    parallel --timeout $MAXTIME -j10 ssh syllable true ::: {1..10} 2>/dev/null >/dev/null &
    parallel --timeout $MAXTIME -j10 ssh pidora true ::: {1..10} 2>/dev/null >/dev/null &
    POLAR_ALL="`bin/parallel --memfree 100m -j0 -k --timeout 10 echo {} ::: $P`"
    POLAR="`bin/parallel --memfree 100m -j0 -k --timeout 10 $PARALLEL_SSH {} echo {} ::: $P`"
    diff <(echo "$POLAR_ALL") <(echo "$POLAR")
    S_POLAR=`bin/parallel -j0 $RET_TIME_K echo -S 1/{} ::: $POLAR`

    sshwithpass() {
	# Minix requires sshpass. The other servers will use ssh-keys
	host="$1"
	shift
	if [ "$host" == "minix" ] ; then
	    q="$(parallel --shellquote ::: "$@")"
	    # This only works from suse and redhat
	    ssh -T -oLogLevel=quiet suse \
		sshpass -f ~/.ssh/minix.password ssh -T -oLogLevel=quiet $host $q
	else
	    ssh -oLogLevel=quiet $host "$@"
	fi
    }
    export -f sshwithpass
    
    copy() {
	# scp, but atomic (avoid half files if disconnected)
	host=$1
	src="$2"
	dst="$3"
	cat "$src" |
	    sshwithpass $host "mkdir -p bin;cat > bin/'$dst'.tmp && chmod 755 bin/'$dst'.tmp && mv bin/'$dst'.tmp bin/'$dst'" 2>&1
    }
    export -f copy

    par_nonall() {
	parallel -j$MAXPROC $RET_TIME_K --delay 0.1 --tag \
		 --nonall $S_POLAR -S "1/sshwithpass minix" --argsep ,:- \
		 'source ./setupenv 2>/dev/null; . `pwd`/setupenv;' "$@"
	# setupenv contains something like this (adapted to the local path and shell)
	#
	# PATH=$HOME/bin:$PATH:/usr/local/bin
	# export PATH
	# . bin/env_parallel.sh
    }
    export -f par_nonall

    echo '### Copy commands to servers'
    # Dont copy stdout - it depends on /bin/bash
    env_parallel -j$MAXPROC $RET_TIME_K --delay 0.03 --tag copy {2} {1} {1/} \
	     ::: bin/{parallel,env_parallel,env_parallel.*[^~],parcat} \
	     ::: $POLAR minix
    echo Done copying

    env_parallel -d '\n\n' -vkj$MAXINNERPROC --delay 2 <<'EOF' |

    echo
    echo '### Works on ...'
    echo
    par_nonall parallel echo Works on {} ::: '`hostname`' 2>&1

    echo
    echo '### --number-of-cores/--number-of-cpus should work with no error'
    echo
    par_nonall 'parallel --number-of-sockets; parallel --number-of-cores' 2>&1
    par_nonall 'parallel --number-of-threads; parallel --number-of-cpus' 2>&1

    echo
    echo '### Fails if tmpdir is R/O'
    echo
    par_nonall "stdout parallel --tmpdir / echo ::: test read-only tmp |
	        perl -pe '\$exit += s:/[a-z0-9_]+.arg:/XXXXXXXX.arg:gi; \$exit += s/[0-9][0-9][0-9][0-9]/0000/gi; END { exit not \$exit }' &&
	        echo OK readonly tmp" 2>&1

    echo
    echo '### Does exporting a bash function make parallel fail?'
    echo 'If login shell is not bash compatible it fails'
    echo
    # http://zmwangx.github.io/blog/2015-11-25-bash-function-exporting-fiasco.html
    par_nonall 'echo test funcA
        funcA() {
            cat <(echo bash only A)
        }
        export -f funcA;
        bin/parallel funcA ::: 1' 2>&1 | LANG=C sort

    echo
    echo '### Does PARALLEL_SHELL help exporting a bash function'
    echo 'If login shell is not bash compatible it should work'
    echo
    mkdir -p tmp/bin
    cp /bin/bash tmp/bin
    cd tmp
    export PARALLEL_SHELL=bin/bash
    par_nonall 'echo test funcB
        funcB() {
            cat <(echo bash only B)
        }
        export -f funcB
        export PARALLEL_SHELL=bin/bash
        bin/parallel funcB ::: 1' 2>&1

    echo
    echo '### env_parallel --install'
    echo '(bash ksh mksh zsh only)'
    echo
    par_nonall 'bin/env_parallel --install && echo install-OK' 2>&1

    echo
    echo '### env_parallel echo env_parallel ::: run-OK'
    echo '(bash ksh mksh zsh only)'
    echo
    par_nonall 'env_parallel echo env_parallel ::: run-OK' 2>&1

    echo
    echo '### env_parallel echo reading from process substitution :::: <(echo OK)'
    echo '(bash ksh mksh zsh only)'
    echo
    # csh on NetBSD does not support process substitution 
    par_nonall 'env_parallel echo reading from process substitution :::: <(echo OK)' 2>&1 | 
	grep -v ': /tmp/.*: No such file or directory'

    echo
    echo '### Test empty command name in process list'
    echo '(bash ksh mksh zsh only)'
    echo
    test_empty_cmd() {
	echo '### Test if empty command name in process list causes problems'
	perl -e '$0=" ";sleep 1000' &
        pid=$!
	parallel echo ::: OK_with_empty_cmd
        kill $pid
    }
    export -f test_empty_cmd
    export PARALLEL_SHELL=bin/bash
    PARALLEL='--env test_empty_cmd' par_nonall test_empty_cmd 2>&1

    echo
    echo '### parset arr seq ::: 2 3 4'
    echo '(bash ksh mksh zsh only)'
    echo
    par_nonall 'parset arr seq ::: 2 3 4; echo ${arr[*]}' 2>&1
    echo '### env_parset arr seq ::: 2 3 4'
    par_nonall 'start=2;env_parset arr seq \$start ::: 2 3 4; echo ${arr[*]}' 2>&1

    echo
    echo '### parset var1,var2,var3 seq ::: 2 3 4'
    echo '(bash ksh mksh zsh ash dash only)'
    echo
    par_nonall 'parset var1,var2,var3 seq ::: 2 3 4; echo $var1,$var2,$var3' 2>&1
    echo '### env_parset var1,var2,var3 seq ::: 2 3 4'
    par_nonall 'start=2; env_parset var1,var2,var3 seq \$start ::: 2 3 4; echo $var1,$var2,$var3' 2>&1
EOF
    perl -ne 'm{UX:sh ./bin/sh.: ERROR: source: Not found} and next;
    	      m{/usr/X11R7/bin/.: Permission denied.} and next;
    print'
}

env_parallel -u -S$MASTER doit ::: 1|
    perl -pe 's:/home/(t/)?tange:~:g' |
    perl -pe 's:par-job-\d+_\w+:parScript:g'

# eval 'myfunc() { echo '$(perl -e 'print "x"x20000')'; }'
# env_parallel myfunc ::: a | wc # OK
# eval 'myfunc2() { echo '$(perl -e 'print "x"x120000')'; }'
# env_parallel myfunc ::: a | wc # Fail too big env

# Supported SSH keylength:
# 16300: 
#   debian-ppc netbsd openbsd qnx aix centos freebsd hpux hpux-ia64
#   macosx mandriva miros raspbian redhat scosysv suse tru64 unixware
# 8000:
#   solaris-x86
# 4000:
#   openindiana solaris


