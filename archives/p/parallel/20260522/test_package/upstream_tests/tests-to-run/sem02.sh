#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

minipv() {
    sleep=$1
    while read line; do
	echo "$line"
	sleep $sleep
    done
}
export -f minipv

echo '### Test id = --id `tty`'
parallel --id `tty` --lb --semaphore seq  1 10 '|' minipv 0.1
echo '### Test default id = --id `tty`'
parallel            --lb --semaphore seq 11 20 '|' minipv 0.01
echo '### Test --semaphorename `tty`'
parallel --semaphorename `tty` --semaphore --wait
echo done
