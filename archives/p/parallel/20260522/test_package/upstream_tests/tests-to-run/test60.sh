#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

SERVER1=parallel-server1
SERVER2=parallel-server2
SSHUSER1=vagrant
SSHUSER2=vagrant
export SSHLOGIN1=$SSHUSER1@$SERVER1
export SSHLOGIN2=$SSHUSER2@$SERVER2

par_onall() {
    echo '### Test --onall'
    parallel --onall -S $SSHLOGIN1,$SSHLOGIN2 '(echo {1} {2}) | awk \{print\ \$2}' ::: a b c ::: 1 2
}

par_pipe_onall() {
    echo '### Test | --onall'
    seq 3 | parallel --onall -S $SSHLOGIN1,$SSHLOGIN2 '(echo {1} {2}) | awk \{print\ \$2}' ::: a b c :::: -
}

par_onall_u() {
    echo '### Test --onall -u'
    parallel --onall -S $SSHLOGIN1,$SSHLOGIN2 -u '(echo {1} {2}) | awk \{print\ \$2}' ::: a b c ::: 1 2 3 | sort
}

par_nonall() {
    echo '### Test --nonall'
    parallel --nonall -k -S $SSHLOGIN1,$SSHLOGIN2 'hostname' | sort
}

par_nonall_sshloginfile_stdin() {
    echo '### Test read sshloginfile from STDIN'
    echo $SSHLOGIN1 | parallel -S - --nonall hostname; 
    echo $SSHLOGIN1 | parallel --sshloginfile - --nonall hostname
}

par_nonall_basefile() {
    echo '### Test --nonall --basefile'
    touch /tmp/nonall--basefile
    parallel --nonall --basefile /tmp/nonall--basefile -S $SSHLOGIN1,$SSHLOGIN2 ls /tmp/nonall--basefile\; rm  /tmp/nonall--basefile
    rm /tmp/nonall--basefile
}

par_onall_basefile() {
    echo '### Test --onall --basefile'
    touch /tmp/onall--basefile
    parallel --onall --basefile /tmp/onall--basefile -S $SSHLOGIN1,$SSHLOGIN2 ls {}\; rm {} ::: /tmp/onall--basefile
    rm /tmp/onall--basefile
}

par_workdir() {
    echo '### Test --workdir .'
    ssh $SSHLOGIN1 mkdir -p mydir
    mkdir -p $HOME/mydir; cd $HOME/mydir
    parallel --workdir . -S $SSHLOGIN1 ::: pwd
}

par_wd() {
    echo '### Test --wd .'
    ssh $SSHLOGIN2 mkdir -p mydir
    mkdir -p $HOME/mydir; cd $HOME/mydir
    parallel --workdir . -S $SSHLOGIN2 ::: pwd
}

export -f $(compgen -A function | grep par_)
#compgen -A function | grep par_ | sort | parallel --delay $D -j$P --tag -k '{} 2>&1'
compgen -A function | grep par_ | sort |
    parallel --joblog /tmp/jl-`basename $0` --retries 3 -j300% --tag -k '{} 2>&1' |
    perl -pe "s/‘/'/g;s/’/'/g"
