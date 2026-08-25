#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel -vj0 -k --joblog /tmp/jl-`basename $0` -L1 -r
echo '### This causes problems if we kill child processes'; 
# 2>/dev/null to avoid parallel: Warning: Starting 45 processes took > 2 sec.
  seq 2 40 | parallel -j 0 seq 1 10 2>/dev/null | sort | md5sum

echo '### This causes problems if we kill child processes (II)'; 
# 2>/dev/null to avoid parallel: Warning: Starting 45 processes took > 2 sec.
  seq 1 40 | parallel -j 0 seq 1 10 '| parallel -j 3 echo' 2>/dev/null | LC_ALL=C sort | md5sum

echo '### Test -m'; 
  (echo foo;echo bar) | parallel -j1 -m echo 1{}2{}3 A{}B{}C

echo '### Test -X'; 
  (echo foo;echo bar) | parallel -j1 -X echo 1{}2{}3 A{}B{}C

echo '### Bug before 2009-08-26 causing regexp compile error or infinite loop'; 
  echo a | parallel -qX echo  "'"{}"' "

echo '### Bug before 2009-08-26 causing regexp compile error or infinite loop (II)'; 
  echo a | parallel -qX echo  "'{}'"

echo '### bug #42041: Implement $PARALLEL_JOBSLOT'
  parallel -k --slotreplace // -j2 sleep 1\;echo // ::: {1..4} | sort
  parallel -k -j2 sleep 1\;echo {%} ::: {1..4} | sort

echo '### bug #42363: --pipepart and --fifo/--cat does not work'
  seq 100 > /tmp/bug42363; 
  parallel --pipepart --block 31 -a /tmp/bug42363 -k --fifo 'cat {} | wc'; 
  parallel --pipepart --block 31 -a /tmp/bug42363 -k --cat  'cat {} | wc'; 
  rm /tmp/bug42363

echo '### bug #42893: --block should not cause decimals in cat_partial'
  seq 100000 >/tmp/parallel-decimal; 
  parallel --dry-run -kvv --pipepart --block 0.12345M -a /tmp/parallel-decimal true; 
  rm /tmp/parallel-decimal

echo '### bug #42892: parallel -a nonexiting --pipepart'
  parallel --pipepart -a nonexisting wc

echo '### added transfersize/returnsize to local jobs'
  echo '### normal'
  seq 100 111 | parallel --joblog /dev/stderr seq {} '|' pv -qL100 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --line-buffer'
  seq 100 111 | parallel --joblog /dev/stderr --line-buffer seq {} '|' pv -qL100 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --tag'
  seq 100 111 | parallel --tag --joblog /dev/stderr seq {} '|' pv -qL100 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --tag --line-buffer'
  seq 100 111 | parallel --tag --line-buffer --joblog /dev/stderr seq {} '|' pv -qL100 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --files'
  seq 100 111 | parallel --files --joblog /dev/stderr seq {} '|' pv -qL100 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --files --tag'
  seq 100 111 | parallel --files --tag --joblog /dev/stderr seq {} '|' pv -qL100 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --pipe'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 --pipe pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --pipe --line-buffer'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 --pipe --line-buffer pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --pipe --tag'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 --pipe --tag pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --pipe --tag --line-buffer'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 --pipe --tag --line-buffer pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --files --pipe'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 --files --pipe pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --files --pipe --tag'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 --files --pipe --tag pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort
  echo '### --pipe --round-robin'
  seq 1000 | parallel --joblog /dev/stderr --block 1111 -j2 --pipe --round-robin pv -qL300 2>&1 >/dev/null | cut -f 5-7 | sort


EOF

