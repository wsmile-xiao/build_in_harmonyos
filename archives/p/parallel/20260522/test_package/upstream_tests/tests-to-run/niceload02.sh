#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo '### Test niceload exit code'
niceload "perl -e 'exit(3)'" ; echo $? eq 3
niceload "perl -e 'exit(0)'" ; echo $? eq 0

# force load > 10
while uptime | grep -v age:.[1-9][0-9].[0-9][0-9] >/dev/null ; do
    (timeout 5 nice perl -e 'while(1){}' 2>/dev/null &)
done

echo '### Test -p'
perl -e '$|=1;while($t++<3){sleep(1);print "."}' &
# The above will normally take 3.6 sec
# It should be suspended so it at least takes 5 seconds
stdout /usr/bin/time -f %e niceload -l 8 -p $! | perl -ne '$_ >= 5 and print "OK\n"'

par_sensor_-l_negative() {
    echo "### Test --sensor -l negative"
    # When the size is bigger, then run
    TMPDIR=/tmp
    sizet=$(mktemp)
    rm -f "$sizet"
    tmux new-session -d -n 10 "seq 10000 | pv -qL 1000 > $sizet"
    niceload -t .01 --sensor "stat -c %b $sizet" -l -10 "stat -c %b $sizet" |
	perl -ne 'print (($_ >= 10) ? "OK\n" : "Fail: $_\n" )'
    rm "$sizet"
}

par_sensor_-l_negative
