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

echo '### Test $PARALLEL'
parallel_orig=$PARALLEL
PARALLEL="$parallel_orig -k
-j1
echo" parallel ::: a b c

PARALLEL="$parallel_orig -k
--jobs
1
echo" parallel ::: a b c

PARALLEL="$parallel_orig -k
--jobs 1
echo" parallel ::: a b c

PARALLEL="$parallel_orig -k
--jobs
1
echo 1" parallel -v echo 2 ::: a b c

PARALLEL="$parallel_orig -k --jobs 1 echo" parallel ::: a b c
PARALLEL="$parallel_orig -k --jobs 1 echo 1" parallel -v echo 2 ::: a b c

echo '### Test ugly quoting from $PARALLEL'
PARALLEL="$parallel_orig -k --jobs 1 perl -pe \'\$a=1; print\$a\'" parallel -v ::: <(echo a) <(echo b)
PARALLEL="$parallel_orig -k --jobs 1 -S $SSHLOGIN1"' perl -pe \"\\$a=1; print\\$a\"' parallel -v '<(echo {})' ::: foo

echo '### Test ugly quoting from profile file'
cat <<EOF >~/.parallel/test_profile
# testprofile
-k --jobs 1 perl -pe \'\$a=1; print \$a\'
EOF
parallel -v -J test_profile ::: <(echo a) <(echo b)

echo '### Test ugly quoting from profile file --plain'
parallel -v -J test_profile --plain echo ::: <(echo a) <(echo b)

PARALLEL="$parallel_orig -k --jobs 1 echo" parallel -S ssh\ $SSHLOGIN1 -v ::: foo
PARALLEL="$parallel_orig "'-k --jobs 1 perl -pe \"\\$a=1; print \\$a\"' parallel -S ssh\ $SSHLOGIN1 -v '<(echo {})' ::: foo

echo '### Test quoting of $ in command from profile file'
cat <<EOF >~/.parallel/test_profile
-k --jobs 1 perl -pe \'\\\$a=1; print \\\$a\'
EOF
parallel -v -J test_profile -S ssh\ $SSHLOGIN1 '<(echo {})' ::: foo

echo '### Test quoting of $ in command from profile file --plain'
parallel -v -J test_profile --plain -S ssh\ $SSHLOGIN1 'cat <(echo {})' ::: foo

echo '### Test quoting of $ in command from $PARALLEL'
PARALLEL="$parallel_orig "'-k --jobs 1 perl -pe \"\\$a=1; print \\$a\" ' parallel -S ssh\ $SSHLOGIN1 -v '<(echo {})' ::: foo

echo '### Test quoting of $ in command from $PARALLEL --plain'
PARALLEL="$parallel_orig "'-k --jobs 1 perl -pe \"\\$a=1; print \\$a\" ' parallel --plain -S ssh\ $SSHLOGIN1 -v 'cat <(echo {})' ::: foo

echo '### Test quoting of space in arguments (-S) from profile file'
cat <<EOF >~/.parallel/test_profile
-k --jobs 1 -S ssh\ $SSHLOGIN1 perl -pe \'\$a=1; print \$a\'
EOF
parallel -v -J test_profile '<(echo {})' ::: foo

echo '### Test quoting of space in arguments (-S) from profile file --plain'
parallel -v -J test_profile --plain 'cat <(echo {})' ::: foo

echo '### Test quoting of space in arguments (-S) from $PARALLEL'
PARALLEL="$parallel_orig "'-k --jobs 1 -S ssh\ '$SSHLOGIN1' perl -pe \"\\$a=1; print \\$a\" ' parallel -v '<(echo {})' ::: foo

echo '### Test quoting of space in long arguments (--sshlogin) from profile file'
cat <<EOF >~/.parallel/test_profile
# testprofile
-k --jobs 1 --sshlogin ssh\ $SSHLOGIN1 perl -pe \'\$a=1; print \$a\'
EOF
parallel -v -J test_profile '<(echo {})' ::: foo

echo '### Test quoting of space in arguments (-S) from $PARALLEL'
PARALLEL="$parallel_orig "'-k --jobs 1 --sshlogin ssh\ '$SSHLOGIN1' perl -pe \"\\$a=1; print \\$a\" ' parallel -v '<(echo {})' ::: foo

echo '### Test merging of profiles - sort needed because -k only works on the single machine'
echo --tag > ~/.parallel/test_tag
echo -S .. > ~/.parallel/test_S..
echo $SSHLOGIN1 > ~/.parallel/sshloginfile
echo $SSHLOGIN2 >> ~/.parallel/sshloginfile
parallel -Jtest_tag -Jtest_S.. --nonall echo a | sort

echo '### Test merging of profiles - sort needed because -k only works on the single machine --plain'
parallel --plain -Jtest_tag -Jtest_S.. --nonall echo a | sort
