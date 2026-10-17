#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

cpuburn=$(mktemp)
qcpuburn=$(parallel -0 --shellquote ::: "$cpuburn")
(echo '#!/usr/bin/perl'
 echo "eval{setpriority(0,0,9)}; while(1){}") > "$cpuburn"
chmod 700 "$cpuburn"
basename=$(basename "$cpuburn")

forceload () {
  # Force load
  LOAD=$1
  # Start 10 times as many cpuburn
  seq 0 0.1 $1 | parallel -j0 timeout 20 "$qcpuburn" 2>/dev/null &
  PID=$!
  # Give GNU Parallel 1 second to startup
  sleep 1
  perl -e 'do{$a=`uptime`} while($a=~/average: *(\S+)/ and $1 < '$LOAD')'
  # Load is now > $LOAD
}

# Force load avg > number of cpu cores
forceload $(parallel --number-of-cores)

cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel -vj0 -k --joblog /tmp/jl-`basename $0` -L1 -r
echo "bug #38441: CPU usage goes to 100% if load is higher than --load at first job"
/usr/bin/time -f %e parallel --load 100% true ::: a 2>&1 | 
  perl -ne '$_ > 1 and print "More than 1 secs wall clock: OK\n"'

/usr/bin/time -f %U parallel --load 100% true ::: a 2>&1 | 
  perl -ne '$_ < 1 and print "Less than 1 secs user time: OK\n"'

echo '### Test slow arguments generation - https://savannah.gnu.org/bugs/?32834'
  seq 1 3 | parallel -j1 "sleep 2; echo {}" | parallel -kj2 echo
EOF

# Make sure we got all the cpuburn killed
killall "$basename" 2>/dev/null

echo '### Test too slow spawning'
# Let the commands below run during high load
seq 1000 | timeout 20 parallel -j400% -N0 "$qcpuburn" 2>/dev/null &
PID=$!
seq 1 1000 | stdout nice nice parallel --halt 1 -uj0 -N0 kill $PID | 
  perl -pe '/parallel: Warning: Starting \d+ processes took/ and do {close STDIN; `kill '$PID';killall "$basename"`; print "OK\n"; exit }'; 

# Make sure we got all the cpuburn killed
killall "$basename" 2>/dev/null
rm "$cpuburn"
