#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Make a dir that is easy to fill up
SHM=/tmp/shm/parallel-local14
mkdir -p $SHM

check_disk_is_filling() {
    # Run df every 0.1 second for 20 seconds
    seq 1 200 |
	parallel --delay 0.1 -N0 -I // -j1 df $SHM |
	grep --line-buffer $SHM |
#	tee /dev/tty |
	perl -a -F'\s+' -ne '$a ||=$F[3]; $b=$F[3];
    	   if ($a-1000 > $b) { print "More than 1 MB gone. Good!\n";exit }'
}

mytest() {
    # '' or TMPDIR=$SHM or TMPDIR=/tmp
    env="$1"
    # '' or --tmpdir $SHM
    arg="$2"

    sudo umount -l $SHM 2>/dev/null
    sudo mount -t tmpfs -o size=10% none $SHM
    eval export $env
    parallel --timeout 15 $arg pv -qL10m {} ::: /dev/zero >/dev/null &
    PID=$!
    TMPDIR=/tmp
    check_disk_is_filling
    kill -TERM $PID
    sudo umount -l $SHM
}

echo '### Test --tmpdir'
mytest 'Dummy=dummy' "--tmpdir $SHM"

echo '### Test $TMPDIR'
mytest TMPDIR=$SHM ""

echo '### Test $TMPDIR and --tmpdir'
mytest TMPDIR=/tmp "--tmpdir $SHM"
