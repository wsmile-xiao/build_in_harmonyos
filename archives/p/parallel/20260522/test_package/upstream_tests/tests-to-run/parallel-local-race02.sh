#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# These fail regularly

par_totaljob_repl() {
    echo '{##} bug #45841: Replacement string for total no of jobs'

    parallel -k --plus echo {##} ::: {a..j};
    parallel -k 'echo {= $::G++ > 3 and ($_=$Global::JobQueue->total_jobs());=}' ::: {1..10}
    parallel -k -N7 --plus echo {#} {##} ::: {1..14}
    parallel -k -N7 --plus echo {#} {##} ::: {1..15}
    parallel -k -S 8/: -X --plus echo {#} {##} ::: {1..15}
    parallel -k --plus --delay 0.01 -j 10 'sleep 2; echo {0#}/{##}:{0%}' ::: {1..5} ::: {1..4}
}

par_semaphore() {
    echo '### Test if parallel invoked as sem will run parallel --semaphore'
    sem --id as_sem -u -j2 'echo job1a 1; sleep 3; echo job1b 3'
    sleep 0.5
    sem --id as_sem -u -j2 'echo job2a 2; sleep 3; echo job2b 5'
    sleep 0.5
    sem --id as_sem -u -j2 'echo job3a 4; sleep 3; echo job3b 6'
    sem --id as_sem --wait
    echo done
}

par_sql_CSV() {
    echo '### CSV write to the right place'
    rm -rf /tmp/parallel-CSV
    mkdir /tmp/parallel-CSV
    parallel --sqlandworker csv:///%2Ftmp%2Fparallel-CSV/OK echo ::: 'ran OK'
    ls /tmp/parallel-CSV
    stdout parallel --sqlandworker csv:///%2Fmust%2Ffail/fail echo ::: 1 |
	perl -pe 's/\d/0/g'
}


par_kill_hup() {
    echo '### Are children killed if GNU Parallel receives HUP? There should be no sleep at the end'

    parallel -j 2 -q bash -c 'sleep {} & pid=$!; wait $pid' ::: 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 &
    T=$!
    sleep 3.9
    pstree $$
    kill -HUP $T
    sleep 4
    pstree $$
}

par_resume_failed_k() {
    echo '### bug #38299: --resume-failed -k'
    tmp=$(mktemp)
    parallel -k --resume-failed --joblog "$tmp" echo job{#} val {}\;exit {} ::: 0 1 2 3 0 1
    echo try 2. Gives failing - not 0
    parallel -k --resume-failed --joblog "$tmp" echo job{#} val {}\;exit {} ::: 0 1 2 3 0 1
    echo with exit 0
    parallel -k --resume-failed --joblog "$tmp" echo job{#} val {}\;exit 0  ::: 0 1 2 3 0 1
    sleep 0.5
    echo try 2 again. Gives empty
    parallel -k --resume-failed --joblog "$tmp" echo job{#} val {}\;exit {} ::: 0 1 2 3 0 1
    rm "$tmp"
}

par_testhalt() {
    testhalt_false() {
	echo '### testhalt --halt '$1;
	(yes 0 | head -n 10; seq 10) |
	    stdout parallel -kj4 --delay 0.27 --halt $1 \
		   'echo job {#}; sleep {= $_=0.3*($_+1+seq()) =}; exit {}'; echo $?;
    }
    testhalt_true() {
	echo '### testhalt --halt '$1;
	(seq 10; yes 0 | head -n 10) |
	    stdout parallel -kj4 --delay 0.17 --halt $1 \
		   'echo job {#}; sleep {= $_=0.3*($_+1+seq()) =}; exit {}'; echo $?;
    };
    export -f testhalt_false;
    export -f testhalt_true;

    stdout parallel -k --delay 0.11 --tag testhalt_{4} {1},{2}={3} \
	::: now soon ::: fail success done ::: 0 1 2 30% 70% ::: true false |
	# Remove lines that only show up now and then
	perl -ne '/Starting no more jobs./ or print'
}

par__compress_prg_fails() {
    echo "### bug #41609: --compress fails"
    seq 12 | parallel --compress --compress-program gzip -k seq {} 10000 | md5sum
    seq 12 | parallel --compress -k seq {} 10000 | md5sum

    echo '### bug #44546: If --compress-program fails: fail'
    doit() {
	(parallel $* --compress-program false \
		  echo \; sleep 1\; ls ::: /no-existing
	echo $?) | tail -n1
    }
    export -f doit
    stdout parallel --tag -k doit ::: '' --line-buffer ::: '' --tag ::: '' --files |
	grep -v -- -dc
}

export -f $(compgen -A function | grep par_)
compgen -A function | G "$@" | grep par_ | sort |
    #    parallel --joblog /tmp/jl-`basename $0` -j10 --tag -k '{} 2>&1'
        parallel -o --joblog /tmp/jl-`basename $0` -j1 --tag -k '{} 2>&1'
