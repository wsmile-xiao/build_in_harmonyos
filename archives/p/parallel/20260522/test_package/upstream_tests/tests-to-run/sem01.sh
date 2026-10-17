#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_stdin() {
    echo '### bug #60579: Sem: Allow reading from stdin and setting -a'
    seq 10 | parallel --semaphore --id stdin wc
    seq 10 | parallel --semaphore --id stdin --fg wc
    tmp=$(mktemp)
    seq 10 > "$tmp"
    parallel -a "$tmp" --semaphore --id stdin wc
    parallel -a "$tmp" --semaphore --id stdin --fg wc
    parallel --semaphore --id stdin --wait
    # Should fail: More files are not supported
    parallel -a "$tmp" -a "$tmp" --semaphore --id stdin --fg wc
}

par_mutex() {
    echo '### Test mutex. This should not mix output'
    parallel --semaphore --id mutex -u seq 1 10 '|' pv -qL 20
    parallel --semaphore --id mutex -u seq 11 20 '|' pv -qL 100
    parallel --semaphore --id mutex --wait
    echo done
}

par_fg_then_bg() {
    echo '### Test --fg followed by --bg'
    parallel -u --id fgbg --fg --semaphore seq 1 10 '|' pv -qL 30
    parallel -u --id fgbg --bg --semaphore seq 11 20 '|' pv -qL 30
    parallel -u --id fgbg --fg --semaphore seq 21 30 '|' pv -qL 30
    parallel -u --id fgbg --bg --semaphore seq 31 40 '|' pv -qL 30
    sem --id fgbg --wait
}

par_bg_p_should_error() {
    echo '### Test bug #33621: --bg -p should give an error message'
    stdout parallel -p --bg echo x{}
}

par_fg_line-buffer() {
    echo '### Failed on 20141226'
    sem --fg --line-buffer --id bugin20141226 echo OK
}

par__semaphore-timeout() {
    echo '### Test --st +1/-1'
    # A normal-start
    # parallel: Warning: Semaphore timed out. Stealing the semaphore.
    # B st1-start
    # C normal-end
    # D st1-end
    # parallel: Warning: Semaphore timed out. Exiting.
    (
	stdout sem --id st --line-buffer "echo A normal-start;sleep 6;echo C normal-end"
	stdout sem --id st --line-buffer --st 2 "echo B st1-start;sleep 5;echo D st1-end"
	stdout sem --id st --line-buffer --st -2 "echo ERROR-st-1-start;sleep 5;echo ERROR-st-1-end"
	stdout sem --id st --wait
    ) | sort
}

par_exit() {
    echo '### Exit values'
    test_exit() {
	stdout sem --fg --id exit$1 exit $1
	echo $?
    }
    export -f test_exit
    parallel --tag -k test_exit ::: 0 1 10 100 101 102 222 255

    echo '### Exit values - signal'
    test_signal() {
	bash -c 'kill -'$1' $$'
	echo Bash exit value $?
	stdout sem --fg --id signal$1 kill -$1 '$$'
	echo Sem exit value $?
    }
    export -f test_signal
    ulimit -c 0
    stdout parallel -j15 -k --timeout 20 --tag test_signal ::: {0..64} |
	perl -pe 's/line 1: *(\d+)/line 1: PID/'
}


export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 120 -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g'
