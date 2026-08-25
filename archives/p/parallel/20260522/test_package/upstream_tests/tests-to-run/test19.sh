#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# TODO return multiple

SERVER1=parallel-server1
SERVER2=parallel-server3
SSHUSER1=vagrant
SSHUSER2=vagrant
#SSHLOGIN1=parallel@$SERVER1
#SSHLOGIN2=parallel@$SERVER2
SSHLOGIN1=$SSHUSER1@$SERVER1
SSHLOGIN2=$SSHUSER2@$SERVER2

echo '### Test --transfer --return --cleanup - files with newline'

rm -rf /tmp/parallel.file*
stdout ssh $SSHLOGIN1 rm -rf 'tmp/parallel.file*'  '/tmp/parallel.file*'
stdout ssh $SSHLOGIN2 rm -rf 'tmp/parallel.file*' '/tmp/parallel.file*'

cd /
echo '### --transfer - file with newline'
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --transfer --sshlogin $SSHLOGIN1,$SSHLOGIN2 cat {}";"rm {}
# Should give: No such file or directory
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*'
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*'
) | sort

echo '### --transfer --cleanup - file with newline'
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --transfer --cleanup --sshlogin $SSHLOGIN1,$SSHLOGIN2 cat {}
# Should give: No such file or directory
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*'
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*'
) | sort

echo '### --return - file with newline'
rm -rf /tmp/parallel.file.*newline*
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --return {}.out --sshlogin $SSHLOGIN1,$SSHLOGIN2 mkdir -p tmp\;echo remote '>' {}.out
ls tmp/parallel*newline*out
rm tmp/parallel*newline*out
# Cleanup remote
stdout ssh $SSHLOGIN1 rm -rf 'tmp/parallel.file*'
stdout ssh $SSHLOGIN2 rm -rf 'tmp/parallel.file*'

echo '### --return --cleanup - file with newline'
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --return {}.out --cleanup --sshlogin $SSHLOGIN1,$SSHLOGIN2 echo remote '>' {}.out
ls tmp/parallel*newline*out
rm tmp/parallel*newline*out
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*' || echo OK
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*' || echo OK
) | sort

echo '### --transfer --return --cleanup - file with newline'
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --transfer --return {}.out --cleanup --sshlogin $SSHLOGIN1,$SSHLOGIN2 cat {} '>' {}.out
ls tmp/parallel*newline*out
rm tmp/parallel*newline*out
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*' || echo OK
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*' || echo OK
) | sort

echo '### --trc - file with newline'
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --trc {}.out --sshlogin $SSHLOGIN1,$SSHLOGIN2 cat {} '>' {}.out
ls tmp/parallel*newline*out
rm tmp/parallel*newline*out
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*' || echo OK
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*' || echo OK
) | sort

echo '### --trc - multiple file with newline'
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k --trc {}.out --trc {}.out2 --sshlogin $SSHLOGIN1,$SSHLOGIN2 cat {} '>' {}.out';'cat {} '>' {}.out2
ls tmp/parallel*newline*out*
rm tmp/parallel*newline*out*
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*' || echo OK
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*' || echo OK
) | sort

echo '### Test use special ssh'
echo 'ssh "$@"; echo "$@" >>/tmp/myssh1-run' >/tmp/myssh1
echo 'ssh "$@"; echo "$@" >>/tmp/myssh2-run' >/tmp/myssh2
chmod 755 /tmp/myssh1 /tmp/myssh2
rm -rf /tmp/myssh1-run /tmp/myssh2-run
echo newline > '/tmp/parallel.file.
newline1'
echo newline > '/tmp/parallel.file.
newline2'
find tmp/parallel*newline* -print0 | stdout parallel -0 -k -j1 --trc {}.out --trc {}.out2 \
  --sshlogin "/tmp/myssh1 $SSHLOGIN1, /tmp/myssh2 $SSHLOGIN2" \
  cat {} '>' {}.out';'cat {} '>' {}.out2
ls tmp/parallel*newline*out*
rm tmp/parallel*newline*out*
echo good if no file
(
    stdout ssh $SSHLOGIN1 ls 'tmp/parallel.file*' || echo OK
    # Should give: No such file or directory
    stdout ssh $SSHLOGIN2 ls 'tmp/parallel.file*' || echo OK
) | sort
echo 'Input for ssh'
cat /tmp/myssh1-run /tmp/myssh2-run |
    perl -pe 's/exec perl - \d/exec perl - 9/g' |
    perl -pe 's/(PID.)\d+/${1}00000/g;s/(SEQ[ =]|line)\d/$1X/g;' | 
    perl -pe 's/\S*parallel-server\S*/one-server/;s:( [0-9a-f]{500,})+( [0-9a-f]+)?: hex:g;'
rm /tmp/myssh1-run /tmp/myssh2-run

rm -rf /tmp/parallel.file*
rm /tmp/myssh1 /tmp/myssh2
