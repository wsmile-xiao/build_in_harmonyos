#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

SERVER1=parallel-server1
SERVER2=parallel-server3
SSHUSER1=vagrant
SSHUSER2=vagrant
SSHLOGIN1=$SSHUSER1@$SERVER1
SSHLOGIN2=$SSHUSER2@$SERVER2
#SSHLOGIN1=parallel@$SERVER1
#SSHLOGIN2=parallel@$SERVER2

echo '### Check -S .. and --serverloginfile ..'
echo $SSHLOGIN1 > ~/.parallel/sshloginfile
echo $SSHLOGIN2 >> ~/.parallel/sshloginfile
seq 1 20 | parallel -k -S .. echo
seq 1 20 | parallel -k --sshloginfile .. echo

echo '### Check warning if --transfer but file not found'
echo /tmp/noexistant/file | stdout parallel -k -S $SSHLOGIN1 --transfer echo

echo '### Transfer for file starting with :'
cd /tmp
(echo ':'; echo file:name; echo file:name.foo; echo file: name.foo; echo file : name.foo;) \
  > /tmp/test18
cat /tmp/test18 | parallel echo content-{} ">" {}
cat /tmp/test18 | parallel -j1 --trc {}.{.} -S $SSHLOGIN1,$SSHLOGIN2,: \
  '(echo remote-{}.{.};cat {}) > {}.{.}'
cat /tmp/test18 | parallel -j1 -k 'cat {}.{.}'

echo '### Check warning if --transfer but not --sshlogin'
echo | stdout parallel -k --transfer echo

echo '### Check warning if --return but not --sshlogin'
echo | stdout parallel -k --return {} echo

echo '### Check warning if --cleanup but not --sshlogin'
echo | stdout parallel -k --cleanup echo

echo '### Test --sshlogin -S --sshloginfile'
echo localhost >/tmp/parallel-sshlogin
seq 1 3 | parallel -k --sshlogin 8/$SSHLOGIN1 -S "7/ssh -l $SSHUSER2 $SERVER2",: --sshloginfile /tmp/parallel-sshlogin echo

echo '### Test --sshloginfile with extra content'
echo "2/ssh -l $SSHUSER2 $SERVER2" >>/tmp/parallel-sshlogin
echo ":" >>/tmp/parallel-sshlogin
echo "#2/ssh -l tange nothing" >>/tmp/parallel-sshlogin
seq 1 10 | parallel -k --sshloginfile /tmp/parallel-sshlogin echo

# Moved to parallel-remote1.sh
#echo '### Check forced number of CPUs being respected'
#seq 1 20 | stdout parallel -k -j+0  -S 1/:,7/$SSHLOGIN1  "hostname; echo {} >/dev/null" | sort

echo '### Check more than 9 simultaneous sshlogins'
seq 1 11 | parallel -k -j0 -S "ssh lo" echo

echo '### Check -S syntax'
seq 1 11 | parallel -k -j100% -S : echo
