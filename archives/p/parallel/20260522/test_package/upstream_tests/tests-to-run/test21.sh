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

echo '### Test $PARALLEL - single line'
seq 300000 | PARALLEL="$PARALLEL --pipe -k" parallel wc
(echo 1; echo 1) | PARALLEL="$PARALLEL -S$SSHLOGIN1 -Sssh\ -l\ $SSHUSER2\ $SERVER2 -j1" parallel -kv hostname\; echo | sort

echo '### Test $PARALLEL - multi line'
(echo 1; echo 1) | PARALLEL="$PARALLEL -S$SSHLOGIN1
-Sssh\ -l\ $SSHUSER2\ $SERVER2
-j1" parallel -kv hostname\; echo | sort

echo '### Test ~/.parallel/config - single line'
echo "-S$SSHLOGIN1 -Sssh\ -l\ $SSHUSER2\ $SERVER2 -j1" > ~/.parallel/config
(echo 1; echo 1) | parallel -kv hostname\; echo | sort

echo '### Test ~/.parallel/config - multi line'
echo "-S$SSHLOGIN1
-Sssh\ -l\ $SSHUSER2\ $SERVER2
-j1" > ~/.parallel/config 
(echo 1; echo 1) | parallel -kv hostname\; echo | sort
rm ~/.parallel/config
