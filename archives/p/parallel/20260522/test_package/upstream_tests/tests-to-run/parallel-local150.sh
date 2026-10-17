#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

mkdir -p tmp
cd tmp


# -L1 will join lines ending in ' '
cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | parallel -vj0 -k --joblog /tmp/jl-`basename $0` -L1 -r
echo '### Bug in --load'; 
  nice parallel -k --load 30 sleep 0.1\;echo ::: 1 2 3

echo '### Test --joblog followed by --resume --joblog'
  rm -f /tmp/joblog; 
  timeout -k 1 1 parallel -j2 --joblog /tmp/joblog sleep {} ::: 1.1 2.2 3.3 4.4 2>/dev/null; 
  parallel -j2 --resume --joblog /tmp/joblog sleep {} ::: 1.1 2.2 3.3 4.4; 
  cat /tmp/joblog | wc -lw; 
  rm -f /tmp/joblog;

echo '### Test --resume --joblog followed by --resume --joblog'; 
  rm -f /tmp/joblog2; 
  timeout -k 1 1 parallel -j2 --resume --joblog /tmp/joblog2 sleep {} ::: 1.1 2.2 3.3 4.4 2>/dev/null; 
  parallel -j2 --resume --joblog /tmp/joblog2 sleep {} ::: 1.1 2.2 3.3 4.4; 
  cat /tmp/joblog2 | wc -lw; 
  rm -f /tmp/joblog2;

echo '### Test --header'
  printf "a\tb\n1.2\t3/4.5" | parallel --colsep "\t" --header "\n" echo {b} {a} {b.} {b/} {b//} {b/.}

echo '### 64-bit wierdness - this did not complete on a 64-bit machine'; 
  seq 1 2 | parallel -j1 'seq 1 1 | parallel true'

echo "### BUG-fix: bash -c 'parallel -a <(seq 1 3) echo'"
  stdout bash -c 'parallel -k -a <(seq 1 3)  echo'

echo "### bug #35268: shell_quote doesn't treats [] brackets correctly"
  touch /tmp/foo1; 
  stdout parallel echo ::: '/tmp/foo[123]'; 
  rm /tmp/foo1


echo '### Test bug #35820: sem breaks if $HOME is not writable'
  echo 'Workaround: use another writable dir'; 
  rm -rf /tmp/.parallel || echo /tmp/.parallel wrong owner?; 
  HOME=/tmp sem echo OK; 
  HOME=/tmp sem --wait; 
  ssh lo 'HOME=/usr/this/should/fail stdout sem echo should fail'
EOF
