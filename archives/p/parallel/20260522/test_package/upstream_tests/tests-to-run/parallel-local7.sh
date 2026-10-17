#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_tmux_filter() {
    # /tmp/parallel-local7/tmsOU2Ig
    replace_tmpdir |    
	perl -pe 's:/tms.....:/tmsXXXXX:;s/ p\d+/pID/;'
}
export -f par_tmux_filter

par_tmux() {
    # Read command line length on stdin
    # The line will be a number of \'s
    (stdout parallel --timeout 10 --tmux --delay 0.03 echo '{}{=$_="\\"x$_=}'; echo $?) |
	par_tmux_filter
}
export -f par_tmux

# Does not work
# cat >/tmp/parallel-local7-script <<EOF
# stdout /usr/bin/time -f %e 
# parallel --tmux --fg sleep ::: 1 2 3
# parallel --tmuxpane --fg sleep ::: 1 2 3
# EOF
# chmod +x /tmp/parallel-local7-script
# echo '### bug #48841: --tmux(pane) --fg should start tmux in foreground'
# stdout /usr/bin/time -f %e script -q -f -c /tmp/parallel-local7-script /dev/null |  perl -ne '$_ >= 26 and $_ <= 45 and print "OK\n"'

cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel -vj8 --delay 1 --timeout 60 --retries 3 -k --joblog /tmp/jl-`basename $0` -L1 -r

echo '### tmux-1.9'
  seq 510 512 | PARALLEL_TMUX=tmux-1.9 par_tmux
  seq 0000 10 510 | PARALLEL_TMUX=tmux-1.9 par_tmux

echo '### tmux-1.9 fails' 
  seq 512 10 2000 | PARALLEL_TMUX=tmux-1.9 par_tmux
  seq 2001 10 3000 | PARALLEL_TMUX=tmux-1.9 par_tmux
  seq 3001 10 4000 | PARALLEL_TMUX=tmux-1.9 par_tmux
  seq 4001 10 4030 | PARALLEL_TMUX=tmux-1.9 par_tm
  echo 4036 | PARALLEL_TMUX=tmux-1.9 par_tmux
  echo 4037 | PARALLEL_TMUX=tmux-1.9 par_tmux
  echo 4038 | PARALLEL_TMUX=tmux-1.9 par_tmux

echo '### tmux-1.8 (fails for all in 20220222'
  seq   1 5 100 | PARALLEL_TMUX=tmux-1.8 par_tmux
  seq 101 5 200 | PARALLEL_TMUX=tmux-1.8 par_tmux
  seq 201 5 300 | PARALLEL_TMUX=tmux-1.8 par_tmux
  seq 301 5 400 | PARALLEL_TMUX=tmux-1.8 par_tmux
  seq 401 5 460 | PARALLEL_TMUX=tmux-1.8 par_tmux

echo '### tmux-1.8 fails'
  echo 462 | PARALLEL_TMUX=tmux-1.8 par_tmux
  echo 463 | PARALLEL_TMUX=tmux-1.8 par_tmux
  echo 464 | PARALLEL_TMUX=tmux-1.8 par_tmux

echo '### tmux-1.8 0..255 ascii'
perl -e 'print map { ($_, map { pack("c*",$_) } grep { $_>=1 && $_!=10 } $_-110..$_),"\n" } 0..255' | 
   PARALLEL_TMUX=tmux-1.8 stdout parallel --tmux --timeout 5 echo | par_tmux_filter; echo $?

echo '### tmux-1.9 0..255 ascii'
perl -e 'print map { ($_, map { pack("c*",$_) } grep { $_>=1 && $_!=10 } 0..$_),"\n" } 0..255' | 
   PARALLEL_TMUX=tmux-1.9 stdout parallel --tmux --timeout 5 echo | par_tmux_filter; echo $?

echo '### Test output ascii'
  rm -f /tmp/paralocal7-ascii*; 
  perl -e 'print map { ($_, map { pack("c*",$_) } grep { $_>=1 && $_!=10 } $_-10..$_),"\n" } 1..255' | stdout parallel --tmux echo {}'>>/tmp/paralocal7-ascii{%}' | par_tmux_filter; 
  sort /tmp/paralocal7-ascii* | md5sum

echo '### Test critical lengths. Must not block'
  seq 140 260 | PARALLEL_TMUX=tmux-1.8 stdout parallel --tmux echo '{}{=$_="&"x$_=}' | par_tmux_filter
  seq 140 260 | PARALLEL_TMUX=tmux-1.9 stdout parallel --tmux echo '{}{=$_="&"x$_=}' | par_tmux_filter
  seq 560 850 | PARALLEL_TMUX=tmux-1.8 stdout parallel --tmux echo '{}{=$_="a"x$_=}' | par_tmux_filter
  seq 560 850 | PARALLEL_TMUX=tmux-1.9 stdout parallel --tmux echo '{}{=$_="a"x$_=}' | par_tmux_filter

EOF

rm -f /tmp/paralocal7*
