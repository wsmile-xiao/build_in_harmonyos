#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

SERVER1=parallel-server1
SERVER2=parallel-server2
SERVER2=parallel-server3
SSHUSER1=vagrant
SSHUSER2=vagrant
SSHUSER3=vagrant
SSHLOGIN1=$SSHUSER1@$SERVER1
SSHLOGIN2=$SSHUSER2@$SERVER2
SSHLOGIN3=$SSHUSER3@$SERVER3

#SERVER1=parallel-server1
#SERVER2=parallel-server2

echo '### Test $PARALLEL_SEQ - local'
seq 1 20 | parallel -kN2 echo arg1:{1} seq:'$'PARALLEL_SEQ arg2:{2}

echo '### Test $PARALLEL_SEQ - remote'
seq 1 20 | parallel -kN2 -S $SSHLOGIN1,$SSHLOGIN2 echo arg1:{1} seq:'$'PARALLEL_SEQ arg2:{2}

echo '### Test $PARALLEL_PID - local'
seq 1 20 | parallel -kN2 echo arg1:{1} pid:'$'PARALLEL_PID arg2:{2} | perl -pe 's/\d{3,}/0/g'

echo '### Test $PARALLEL_PID - remote'
seq 1 20 | parallel -kN2 -S $SSHLOGIN1,$SSHLOGIN2 echo arg1:{1} pid:'$'PARALLEL_PID arg2:{2} | perl -pe 's/\d{3,}/0/g'
