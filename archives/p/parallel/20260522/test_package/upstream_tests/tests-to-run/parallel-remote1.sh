#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

SERVER1=parallel-server1
SERVER2=parallel-server2
SERVER3=parallel-server3
SSHUSER1=vagrant
SSHUSER2=vagrant
SSHUSER3=vagrant
export SSHLOGIN1=$SSHUSER1@$SERVER1
export SSHLOGIN2=$SSHUSER2@$SERVER2
export SSHLOGIN3=$SSHUSER3@$SERVER3

#SERVER1=parallel-server1
#SERVER2=lo
#SSHLOGIN1=parallel@parallel-server1
#SSHLOGIN2=parallel@lo
#SSHLOGIN3=parallel@parallel-server2

par_force_number_of_cpu() {
    echo '### Check forced number of CPUs being respected'
    echo 'ssh is slow, so should only get 7. : should get the rest'
    seq 1 20 |
	stdout parallel -k -j+0  -S 1/:,7/$SSHLOGIN1 "hostname; echo {} >/dev/null" |
	sort | uniq -c | sort | field 1
}

par_special_ssh() {
    echo '### Test use special ssh'
    echo 'TODO test ssh with > 9 simultaneous'
    echo 'ssh "$@"; echo "$@" >>/tmp/myssh1-run' >/tmp/myssh1
    echo 'ssh "$@"; echo "$@" >>/tmp/myssh2-run' >/tmp/myssh2
    chmod 755 /tmp/myssh1 /tmp/myssh2
    seq 1 100 | parallel --sshdelay 0.03 --retries 10 --sshlogin "/tmp/myssh1 $SSHLOGIN1,/tmp/myssh2 $SSHLOGIN2" -k echo
}

par__filter_hosts_different_errors() {
    echo '### --filter-hosts - OK, non-such-user, connection refused, wrong host'
    hostname=$(hostname)
    stdout parallel --nonall --filter-hosts -S localhost,NoUser@localhost,154.54.72.206,"ssh 5.5.5.5" hostname |
	grep -v 'parallel: Warning: Removed' |
	perl -pe "s/$hostname/myhostname/g"
}

par_timeout_retries() {
    echo '### test --timeout --retries'
    # 8.8.8.8 is up but does not allow login - should timeout
    # 8.8.8.9 is down - should timeout
    # 172.27.27.197 is down but on our subnet - should no route to host
    stdout parallel -j0 --timeout 16 --retries 3 -k ssh {} echo {} \
	   ::: 172.27.27.197 8.8.8.8 8.8.8.9 $SSHLOGIN1 $SSHLOGIN2 $SSHLOGIN3 |
	grep -v 'Warning: Permanently added' | puniq
}

par__filter_hosts_no_ssh_nxserver() {
    echo '### test --filter-hosts with server w/o ssh, non-existing server'
    # make them warm so they do not timeout
    ssh $SSHLOGIN1 true
    ssh $SSHLOGIN2 true
    ssh $SSHLOGIN3 true
    stdout parallel -S 192.168.1.197,8.8.8.8,8.8.8.9,$SSHLOGIN1,$SSHLOGIN2,$SSHLOGIN3 --filter-hosts --nonall -k --tag echo |
	grep -v 'parallel: Warning: Removed'
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

par_workdir_in_HOME() {
    echo '### test --workdir . in $HOME'
    cd && mkdir -p parallel-test && cd parallel-test && 
	echo OK > testfile &&
	stdout parallel --workdir . --transfer -S $SSHLOGIN1 cat {} ::: testfile |
	    grep -v 'Permanently added'
}

export -f $(compgen -A function | grep par_)
compgen -A function | G "$@" par_ | LC_ALL=C sort |
    parallel --timeout 3000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g'

  
cat <<'EOF' | sed -e s/\$SERVER1/$SERVER1/\;s/\$SERVER2/$SERVER2/\;s/\$SSHLOGIN1/$SSHLOGIN1/\;s/\$SSHLOGIN2/$SSHLOGIN2/\;s/\$SSHLOGIN3/$SSHLOGIN3/ | parallel -vj100% -k -L1 -r




echo '### TODO: test --filter-hosts proxied through the one host'


EOF
rm /tmp/myssh1 /tmp/myssh2 /tmp/myssh1-run /tmp/myssh2-run

